#!/usr/bin/env python3
# Copyright 2026 The browser Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Derived from the ungoogled-chromium-windows build script,
# Copyright (c) 2019 The ungoogled-chromium Authors, BSD-3-Clause.
"""Builds the browser from source on Windows (x64 only).

Steps, in order:
  1. Clone ungoogled-chromium-windows at the pinned tag into build/ (with its
     ungoogled-chromium submodule) and check out Chromium with its clone.py.
  2. Fetch and unpack the toolchain downloads (LLVM, Rust, ...).
  3. Apply the curated ungoogled-chromium patches, the build fixes and this
     project's patch series from patches/.
  4. Write out/Default/args.gn, bootstrap gn, build bindgen, run ninja.

Re-running the script after step 3 finished skips straight to the build; use
--clean to start over. Widevine is not redistributable, so pass
--widevine-dir to bundle a CDM you obtained yourself; without it the browser
builds with Widevine disabled.
"""

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

UC_WINDOWS_REPO = 'https://github.com/ungoogled-software/ungoogled-chromium-windows.git'
UC_WINDOWS_TAG = '153.0.8010.47-1.1'
CHROMIUM_VERSION = '153.0.8010.47'

ROOT_DIR = Path(__file__).resolve().parent
PATCHES_DIR = ROOT_DIR / 'patches'
BUILD_DIR = ROOT_DIR / 'build'
UC_WINDOWS_DIR = BUILD_DIR / 'ungoogled-chromium-windows'
UC_DIR = UC_WINDOWS_DIR / 'ungoogled-chromium'
# Chromium lives where ungoogled-chromium-windows expects it, so its
# downloads.ini, clone.py and package.py work unchanged.
SOURCE_TREE = UC_WINDOWS_DIR / 'build' / 'src'
DOWNLOADS_CACHE = UC_WINDOWS_DIR / 'build' / 'download_cache'
PATCHED_STAMP = UC_WINDOWS_DIR / 'build' / '.patches-applied'
PATCH_BIN_RELPATH = Path('third_party/git/usr/bin/patch.exe')

# Applied to the ungoogled-chromium checkout before its clone.py runs.
INFRA_FIXES = ['clone-gsutil-ignore-whitespace.patch']
# Applied to Chromium after the curated ungoogled patches.
CHROMIUM_BUILD_FIXES = ['fix-build-refs.patch', 'fix-js-optimizer-pref-redef.patch']

WIDEVINE_FILES = [
    Path('LICENSE'),
    Path('win/x64/manifest.json'),
    Path('win/x64/widevinecdm.dll'),
    Path('win/x64/widevinecdm.dll.sig'),
]


def log(message):
    print('[build] ' + message, flush=True)


def run(*args, cwd=None, check=True):
    log('$ ' + ' '.join(str(a) for a in args))
    return subprocess.run([str(a) for a in args], cwd=cwd, check=check)


# ---------------------------------------------------------------------------
# Visual Studio environment (from ungoogled-chromium-windows)
# ---------------------------------------------------------------------------

def get_vcvars_path(name='64'):
    """Returns the path of vcvars<name>.bat of the latest Visual Studio."""
    vswhere = os.path.expandvars('%ProgramFiles(x86)%\\Microsoft Visual Studio\\Installer\\vswhere.exe')
    result = subprocess.run(
        [vswhere, '-products', '*', '-prerelease', '-latest', '-property', 'installationPath'],
        check=True, stdout=subprocess.PIPE, universal_newlines=True)
    vcvars = Path(result.stdout.strip(), 'VC/Auxiliary/Build/vcvars{}.bat'.format(name))
    if not vcvars.exists():
        raise RuntimeError('Could not find vcvars batch script: {}'.format(vcvars))
    return vcvars


def run_build_process(*args, cwd):
    """Runs a command inside a cmd.exe with the Visual Studio variables set."""
    cmd_input = ['call "%s" >nul' % get_vcvars_path(),
                 'set DEPOT_TOOLS_WIN_TOOLCHAIN=0',
                 ' '.join('"{}"'.format(a) for a in args),
                 'exit\n']
    log('$ ' + ' '.join(str(a) for a in args))
    subprocess.run(('cmd.exe', '/k'), input='\n'.join(cmd_input), check=True,
                   encoding='utf-8', cwd=cwd)


# ---------------------------------------------------------------------------
# Step 1: infrastructure and Chromium checkout
# ---------------------------------------------------------------------------

def clone_infrastructure():
    if (UC_WINDOWS_DIR / 'build.py').exists():
        log('ungoogled-chromium-windows already present')
    else:
        BUILD_DIR.mkdir(parents=True, exist_ok=True)
        run('git', 'clone', '--depth', '1', '--branch', UC_WINDOWS_TAG, UC_WINDOWS_REPO, UC_WINDOWS_DIR)
        run('git', 'submodule', 'update', '--init', '--recursive', '--depth', '1', cwd=UC_WINDOWS_DIR)
    version = (UC_DIR / 'chromium_version.txt').read_text(encoding='utf-8').strip()
    if version != CHROMIUM_VERSION:
        raise RuntimeError('ungoogled-chromium pins Chromium {} but the patches are for {}'
                           .format(version, CHROMIUM_VERSION))
    clone_py = UC_DIR / 'utils' / 'clone.py'
    if '--ignore-whitespace' not in clone_py.read_text(encoding='utf-8'):
        for name in INFRA_FIXES:
            run('git', 'apply', PATCHES_DIR / 'build-fixes' / name, cwd=UC_DIR)


def import_ungoogled_utils():
    sys.path.insert(0, str(UC_DIR / 'utils'))
    import downloads  # pylint: disable=import-outside-toplevel
    import patches  # pylint: disable=import-outside-toplevel
    from _common import USE_REGISTRY, ExtractorEnum, get_logger  # pylint: disable=import-outside-toplevel
    sys.path.pop(0)
    return downloads, patches, USE_REGISTRY, ExtractorEnum, get_logger


def checkout_chromium():
    if (SOURCE_TREE / 'BUILD.gn').exists():
        log('Chromium source already present')
        return
    SOURCE_TREE.parent.mkdir(parents=True, exist_ok=True)
    run(sys.executable, UC_DIR / 'utils' / 'clone.py', '-o', SOURCE_TREE, '-p', 'win64', cwd=UC_WINDOWS_DIR)


# ---------------------------------------------------------------------------
# Step 2: downloads
# ---------------------------------------------------------------------------

def fetch_downloads(args, downloads, ExtractorEnum, get_logger):
    DOWNLOADS_CACHE.mkdir(parents=True, exist_ok=True)
    for var in ('TMP', 'TEMP'):
        Path(os.environ[var]).mkdir(parents=True, exist_ok=True)
    extractors = {ExtractorEnum.SEVENZIP: args.sevenz_path, ExtractorEnum.WINRAR: args.winrar_path}

    log('Downloading toolchain files')
    download_info = downloads.DownloadInfo([UC_WINDOWS_DIR / 'downloads.ini'])
    downloads.retrieve_downloads(download_info, DOWNLOADS_CACHE, None, True, args.disable_ssl_verification)
    try:
        downloads.check_downloads(download_info, DOWNLOADS_CACHE, None)
    except downloads.HashMismatchError as exc:
        get_logger().error('File checksum does not match: %s', exc)
        sys.exit(1)

    # Download targets that sit inside a Chromium submodule survive clone.py's
    # cleanup, and unpacking into a non-empty directory fails. Empty them first.
    for relpath in ('third_party/microsoft_dxheaders/src',
                    'third_party/devtools-frontend/src/third_party/esbuild',
                    'third_party/microsoft_webauthn/src',
                    'third_party/dawn/tools/golang/windows-amd64',
                    'third_party/dawn/tools/golang/windows-arm64'):
        target = SOURCE_TREE / relpath
        if target.exists():
            shutil.rmtree(target)
            target.mkdir()
    log('Unpacking downloads')
    downloads.unpack_downloads(download_info, DOWNLOADS_CACHE, None, SOURCE_TREE, extractors)


# ---------------------------------------------------------------------------
# Step 3: patches
# ---------------------------------------------------------------------------

def series(path):
    return [line.strip() for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.startswith('#')]


def apply_patches(patches, get_logger):
    patch_bin = SOURCE_TREE / PATCH_BIN_RELPATH

    log('Applying the curated ungoogled-chromium patches')
    curated = [PATCHES_DIR / 'ungoogled' / name for name in series(PATCHES_DIR / 'ungoogled' / 'series')]
    patches.apply_patches(curated, SOURCE_TREE, patch_bin_path=patch_bin)

    log('Applying the build fixes')
    patches.apply_patches([PATCHES_DIR / 'build-fixes' / name for name in CHROMIUM_BUILD_FIXES],
                          SOURCE_TREE, patch_bin_path=patch_bin)

    log('Applying the browser patch series')
    ours = sorted(PATCHES_DIR.glob('0*.patch'))
    v8 = sorted((PATCHES_DIR / 'v8').glob('0*.patch'))
    if not ours or not v8:
        raise RuntimeError('patch series not found under {}'.format(PATCHES_DIR))
    # Check everything before touching the tree, so a failure leaves it clean.
    for patch in ours:
        run('git', 'apply', '--check', patch, cwd=SOURCE_TREE)
    for patch in v8:
        run('git', 'apply', '--check', patch, cwd=SOURCE_TREE / 'v8')
    for patch in ours:
        run('git', 'apply', patch, cwd=SOURCE_TREE)
    for patch in v8:
        run('git', 'apply', patch, cwd=SOURCE_TREE / 'v8')
    log('{} patches applied'.format(len(curated) + len(CHROMIUM_BUILD_FIXES) + len(ours) + len(v8)))


def overlay_widevine(widevine_dir):
    """Copies a Widevine CDM the user obtained themselves into the tree."""
    missing = [str(f) for f in WIDEVINE_FILES if not (widevine_dir / f).exists()]
    if missing:
        raise RuntimeError('--widevine-dir is missing: ' + ', '.join(missing))
    log('Bundling the Widevine CDM from {}'.format(widevine_dir))
    shutil.copytree(widevine_dir, SOURCE_TREE / 'third_party' / 'widevine' / 'cdm', dirs_exist_ok=True)


# ---------------------------------------------------------------------------
# Step 4: build
# ---------------------------------------------------------------------------

def install_rust_toolchain():
    """Merges the downloaded Rust toolchains into third_party/rust-toolchain."""
    dst = SOURCE_TREE / 'third_party' / 'rust-toolchain'
    flag_file = dst / 'INSTALLED_VERSION'
    if flag_file.exists():
        return
    log('Installing the Rust toolchain')
    src64 = SOURCE_TREE / 'third_party' / 'rust-toolchain-x64'
    for rust_dir_src in (src64,
                         SOURCE_TREE / 'third_party' / 'rust-toolchain-x86',
                         SOURCE_TREE / 'third_party' / 'rust-toolchain-arm'):
        for dir_to_copy in ('bin', 'lib'):
            if dir_to_copy == 'bin' and rust_dir_src != src64:
                continue
            target_dir = dst / dir_to_copy
            target_dir.mkdir(parents=True, exist_ok=True)
            for cp_src in rust_dir_src.glob('*/{}/*'.format(dir_to_copy)):
                cp_dst = target_dir / cp_src.name
                if cp_src.is_dir():
                    shutil.copytree(cp_src, cp_dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(cp_src, cp_dst)
    with open(flag_file, 'w', encoding='utf-8') as f:
        subprocess.run([str(src64 / 'rustc' / 'bin' / 'rustc.exe'), '--version'], stdout=f, check=True)


def write_args_gn(widevine):
    out_dir = SOURCE_TREE / 'out' / 'Default'
    out_dir.mkdir(parents=True, exist_ok=True)
    text = (ROOT_DIR / 'args.gn').read_text(encoding='utf-8')
    if not widevine:
        text = text.replace('bundle_widevine_cdm=true', 'bundle_widevine_cdm=false')
    (out_dir / 'args.gn').write_text(text, encoding='utf-8', newline='\n')


def build(args):
    install_rust_toolchain()
    write_args_gn(args.widevine_dir is not None)
    if not (SOURCE_TREE / 'out' / 'Default' / 'gn.exe').exists():
        run_build_process(sys.executable, 'tools\\gn\\bootstrap\\bootstrap.py',
                          '-o', 'out\\Default\\gn.exe', '--skip-generate-buildfiles', cwd=SOURCE_TREE)
    run_build_process('out\\Default\\gn.exe', 'gen', 'out\\Default', '--fail-on-unused-args', cwd=SOURCE_TREE)
    if not (SOURCE_TREE / 'third_party' / 'rust-toolchain' / 'bin' / 'bindgen.exe').exists():
        run_build_process(sys.executable, 'tools\\rust\\build_bindgen.py', '--skip-test', cwd=SOURCE_TREE)
    ninja = ['third_party\\ninja\\ninja.exe']
    if args.thread_count is not None:
        ninja += ['-j', str(args.thread_count)]
    ninja += ['-C', 'out\\Default', 'chrome', 'chromedriver', 'mini_installer']
    run_build_process(*ninja, cwd=SOURCE_TREE)
    log('Build finished: {}'.format(SOURCE_TREE / 'out' / 'Default'))
    if args.package:
        run(sys.executable, 'package.py', cwd=UC_WINDOWS_DIR)


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-j', type=int, dest='thread_count', help='number of parallel compile jobs')
    parser.add_argument('--widevine-dir', type=Path,
                        help='directory with LICENSE and win/x64/{manifest.json,widevinecdm.dll,'
                             'widevinecdm.dll.sig} to bundle; Widevine is disabled without it')
    parser.add_argument('--package', action='store_true',
                        help='run ungoogled-chromium-windows/package.py after the build')
    parser.add_argument('--clean', action='store_true', help='delete build/ and start over')
    parser.add_argument('--disable-ssl-verification', action='store_true',
                        help='disable SSL verification for downloads')
    parser.add_argument('--7z-path', dest='sevenz_path', default='_use_registry',
                        help='path to 7z.exe; "_use_registry" finds it in the registry (default)')
    parser.add_argument('--winrar-path', dest='winrar_path', default='_use_registry',
                        help='path to winrar.exe; "_use_registry" finds it in the registry (default)')
    args = parser.parse_args()

    if sys.platform != 'win32':
        parser.error('this build script only supports Windows')
    if args.clean and BUILD_DIR.exists():
        log('Removing {}'.format(BUILD_DIR))
        shutil.rmtree(BUILD_DIR)
    if args.widevine_dir is not None:
        args.widevine_dir = args.widevine_dir.resolve()

    clone_infrastructure()
    downloads, patches, _, ExtractorEnum, get_logger = import_ungoogled_utils()

    if PATCHED_STAMP.exists():
        log('Source tree is already prepared; building (use --clean to start over)')
    else:
        checkout_chromium()
        fetch_downloads(args, downloads, ExtractorEnum, get_logger)
        apply_patches(patches, get_logger)
        PATCHED_STAMP.write_text(UC_WINDOWS_TAG + '\n', encoding='utf-8')
    if args.widevine_dir is not None:
        overlay_widevine(args.widevine_dir)
    build(args)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        log('command failed with exit code {}'.format(exc.returncode))
        sys.exit(exc.returncode or 1)
    except RuntimeError as exc:
        log(str(exc))
        sys.exit(1)
