# Anti-Fingerprint Browser

A Chromium build that lets you control what your browser reports about your machine (GPU, canvas, audio, fonts, screen, hardware, timezone) instead of providing a stable, unique fingerprint to every site you visit.

Spoofing happens inside the browser, not through injected JavaScript, so there's no `Object.defineProperty` wrapper for a page to detect. Identities are either random per launch or reproducible from an integer seed.

**Windows only.** Distributed as a binary; the source is the patch series in [`patches/`](patches), applied on top of Chromium.

---

## Contents

- [Download](#download)
- [Source](#source)
- [Install](#install)
- [What this does and doesn't do](#what-this-does-and-doesnt-do)
- [Privacy defaults](#privacy-defaults)
- [Fingerprint identity](#fingerprint-identity)
- [Command-line switches](#command-line-switches)
- [Automation: custom CDP methods](#automation-custom-cdp-methods)
- [Intended use](#intended-use)
- [License](#license)

---

## Download

Grab the latest build from the [Releases page](../../releases):

| File | Description |
|---|---|
| `AntiFingerprintChromium-Setup-<version>.exe` | Installer with Windows integration |
| `AntiFingerprintChromium-<version>-portable.zip` | Portable, no installation |

## Source

Everything this browser changes lives in [`patches/`](patches): one numbered patch per feature, applied in order to the Chromium release named in the patch series. Each patch is self-contained and readable on its own, so you can see exactly what is spoofed and how before you run the binary.

To check the behavior independently, run the browser against [CreepJS](https://abrahamjuliot.github.io/creepjs/), [BrowserScan](https://www.browserscan.com/), or [FingerprintJS](https://demo.fingerprint.com/playground) with spoofing on and off and compare, or watch its network traffic with Wireshark or Fiddler to confirm the telemetry claims.

### Building from source

`build.py` does the whole job: it clones [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows) at the pinned tag, checks out the matching Chromium release with its tooling, fetches the toolchain downloads, applies the curated ungoogled patches followed by this project's patch series, and runs the build.

```
python build.py [-j N] [--widevine-dir DIR] [--package]
```

Requirements, the same as for ungoogled-chromium-windows: Windows 10 or 11 x64, Visual Studio 2026 with the C++ workload and the Windows SDK version Chromium pins (10.0.28000 for this release), Python 3, Git, 7-Zip, around 45 GB of free disk space and 32 GB or more of RAM. A full build takes several hours. Run it from a regular prompt; the script sets up the Visual Studio environment itself. A second run skips the checkout and patching and goes straight to the build; `--clean` starts over.

Two pieces of the released binaries are not in this repository because they cannot be redistributed:

- **Widevine CDM.** Pass `--widevine-dir` with a directory holding the CDM's `LICENSE` and `win/x64/manifest.json`, `widevinecdm.dll` and `widevinecdm.dll.sig` to bundle one you obtained yourself. Without it the build disables Widevine, and the browser still plays DRM content that uses PlayReady on Windows.
- **Font bundle.** `--browser-font-bundle` loads fonts from a `browser_fonts/` directory next to `chrome.exe` at runtime. The release ships a set of fonts; the build does not need them, and the switch simply does nothing when the directory is absent.

The installer and portable zip on the Releases page are packaged separately; `--package` runs the stock ungoogled-chromium-windows packaging instead, which produces an installer and a zip under `build/ungoogled-chromium-windows/build/`.

## Install

### Installer (recommended)

1. Download `AntiFingerprintChromium-Setup-<version>.exe` and run it.
2. Choose an install location (or accept the default) and all-users vs. just-me.
3. It installs the browser, adds Start Menu / desktop shortcuts, and registers it with Windows as a web browser.
4. To make it your default: tick **"Choose … as your default browser"** on the last wizard page, or later open **Settings → Apps → Default apps**, find **Anti-Fingerprint Chromium**, and set it for `http`, `https`, and `.html`.

Uninstall from **Settings → Apps** like any normal program.

Windows SmartScreen may warn on first run, since the build isn't code-signed with an EV certificate.

### Portable (zip)

1. Extract the zip anywhere and run `chrome.exe`, no installation required.
2. *(Optional)* To make the portable copy selectable as your default browser, run the included `register-browser.ps1` from the extracted folder in an **elevated** PowerShell (or add `-PerUser` to register for just your account, no admin needed), then set it in **Settings → Default apps**. Undo any time with `register-browser.ps1 -Unregister`.

## What this does and doesn't do

This browser takes a different approach from Tor Browser and Mullvad Browser.

Tor and Mullvad aim to make every user look **identical**: one large anonymity set where you're indistinguishable from everyone else running the same build. This browser instead gives you a **plausible and distinct** identity. What makes this approach better than Tor and Mullvad is the increased trust sites have in your browser session. Tor and Mullvad experience captchas and blocks on high-security sites because of their aggressive privacy settings. This browser does not have this issue while still providing good protection from cross-site tracking.

What it does not do:

- **It is not a complete anonymity tool.** Your IP address is untouched unless you supply your own proxy or VPN.
- **It does not defeat login-based tracking.** If you sign into an account, the fingerprint is irrelevant.
- **It does not guarantee evasion of any specific anti-bot system.**

### Security tradeoff: Safe Browsing is disabled

The always-on privacy preset **turns off Google Safe Browsing**, which is what normally warns you about phishing pages and malware downloads. This removes a layer of protection for everyday browsing. I turned it off to speed up page load times and decrease network usage.

## Privacy defaults

A telemetry-off + privacy preset is applied automatically on **every** launch, with no flags or shortcuts needed. It turns off pings, background networking, usage/crash reporting, and **keeps Manifest V2 extension support enabled**, so [uBlock Origin](https://github.com/gorhill/ublock) works as it did pre-Chrome-127.

To launch with stock Chromium behavior instead, add `--use-chromium-defaults` (safebrowsing will stay off regardless).

## Fingerprint identity

Fingerprint spoofing is **off by default**. Turn it on at **`chrome://browser-settings`**:

- **Off**: no spoofing (standard Chromium fingerprint).
- **Auto**: a fresh random identity each launch.
- **Fixed seed**: a stable identity derived from a number you choose (the same number reproduces the same identity across launches).

Your choice is saved and applied on **every** launch, no matter how the browser is started, whether by a clicked link, a shortcut, or as your default browser. Restart the browser after changing it. (This is equivalent to the `--fingerprint-seed` switch below; passing `--fingerprint-seed` on the command line overrides the saved value for that one launch.)

Which mode you want depends on the goal. **Auto** breaks correlation between sessions and suits general browsing. **Fixed seed** keeps you consistent to sites that would find a machine whose hardware changes daily more suspicious than one that never changes at all.

## Command-line switches

Most people won't need these: the privacy defaults are automatic and the fingerprint identity is set at `chrome://browser-settings`. The switches below are for finer control. Pass one by adding it to the **Target** field of your browser shortcut. It then applies to launches from *that* shortcut only, while the privacy defaults and the saved fingerprint seed apply to every launch however the browser is started.

Notation in the **Modes** column: `explicit` means a literal value; `auto` randomizes once per launch; `seed:N` derives deterministically from the integer N (same N across two launches produces identical values).

The **Master** column indicates whether the switch activates implicitly when `--fingerprint-seed=auto|<int>` is set with no per-switch override. Switches without a ✓ require explicit opt-in.

<details>
<summary><b>Master / preset switches</b></summary>

| Switch | Modes | Description |
|---|---|---|
| `--fingerprint-seed=auto\|<int>` | auto, integer | Master seed driving every "Master ✓" switch below. `auto` allocates one random seed per launch; `<int>` is reproducible across launches. Usually set persistently via `chrome://browser-settings` rather than here; a command-line value overrides the saved one for that launch. |
| `--use-chromium-defaults` | presence-only | Opt out of the always-on browser-defaults preset for this launch, running with stock Chromium behavior. |

</details>

<details>
<summary><b>Fingerprint switches: activated by <code>--fingerprint-seed</code></b></summary>

These derive from the active profile (a coherent identity picked from an embedded pool) or from pure seed math. All accept per-switch `auto` or `seed:N` for fine-grained control.

| Switch | Modes | Master | What it spoofs |
|---|---|---|---|
| `--fingerprint-gpu-vendor=<string>` | auto, seed:N, explicit | ✓ | `gl.getParameter(UNMASKED_VENDOR_WEBGL)` |
| `--fingerprint-gpu-renderer=<string>` | auto, seed:N, explicit | ✓ | `gl.getParameter(UNMASKED_RENDERER_WEBGL)` |
| `--fingerprint-webgpu-vendor=<string>` | auto, seed:N, explicit | ✓ | `(await navigator.gpu.requestAdapter()).info.vendor`. Derived from the WebGL renderer via Dawn's vendor/device-ID database. |
| `--fingerprint-webgpu-architecture=<string>` | auto, seed:N, explicit | ✓ | `…info.architecture`. Same derivation as vendor. |
| `--fingerprint-hardware-concurrency=<int>` | auto, seed:N, explicit | ✓ | `navigator.hardwareConcurrency` |
| `--fingerprint-device-memory=<int>` | auto, seed:N, explicit | ✓ | `navigator.deviceMemory`. Snapped to `{2,4,8,16,32}`. |
| `--fingerprint-audio-context=<sr,bl,ol,mcc>` | auto, seed:N, explicit | ✓ | `new AudioContext()` properties: `sampleRate`, `baseLatency`, `outputLatency`, `destination.maxChannelCount`. |
| `--fingerprint-battery=<charging,level,ct,dt>` | auto, seed:N, explicit | ✓ | `navigator.getBattery()` fields. Derive branches on the active profile's device type (desktop = always plugged; laptop = sampled). |
| `--fingerprint-connection=<eff,dl,rtt,sd,type>` | auto, seed:N, explicit | ✓ | `navigator.connection` properties + HTTP Client Hint headers (`Downlink`, `RTT`, `ECT`). Format: `effectiveType,downlinkMbps,rttMs,saveData,connectionType`. |
| `--fingerprint-brand=<string>` | auto, seed:N, explicit | ✓ | `navigator.userAgentData.brands[].brand`. Auto default: `"Chrome"`. |
| `--fingerprint-brand-version=<int>` | auto, seed:N, explicit | ✓ | UA `Chrome/<N>.0.0.0` major segment. Auto default: real Chromium major version. |
| `--fingerprint-brand-version-long=<full>` | auto, seed:N, explicit | ✓ | `navigator.userAgentData.getHighEntropyValues(['fullVersionList'])`. Auto default: real `PRODUCT_VERSION`. |
| `--canvas-curve-noise=<float>` | auto, seed:N, explicit | ✓ | Sub-pixel perturbation on Canvas 2D curve verbs (bezier, arc, quadratic). Range `[0.003, 0.015]`. |
| `--canvas-blur-noise=<float>` | auto, seed:N, explicit | ✓ | Multiplicative perturbation on Gaussian blur sigmas (`shadowBlur`, `ctx.filter='blur(...)'`). Range `[0.005, 0.03]`. |
| `--canvas-gradient-noise=<float>` | auto, seed:N, explicit | ✓ | Additive perturbation on Canvas 2D gradient color-stop offsets. Range `[0.003, 0.02]`. |
| `--webgl-shader-noise=<float>` | auto, seed:N, explicit | ✓ | Sub-LSB perturbation on WebGL fragment-shader natural-variance constructs. Range `[1e-3, 3e-3]`. |
| `--browser-font-bundle=<seed-string>` | auto, seed:N, explicit | ✓ | Selects an on-disk font bundle from `browser_fonts/`; affects `document.fonts` enumeration and text metric widths. |

</details>

<details>
<summary><b>Fingerprint switches: explicit opt-in only</b></summary>

These exist but are not activated by `--fingerprint-seed`. Pass them with `=auto`, `=seed:N`, or a literal value to use them.

| Switch | Modes | What it spoofs |
|---|---|---|
| `--fingerprint-screen=<w,h,aw,ah,at,cd[,dpr]>` | auto, seed:N, explicit | `screen.width/height/availWidth/availHeight/availTop/colorDepth` plus `window.devicePixelRatio` (optional 7th field). |
| `--fingerprint-screen-position=<x,y>` | auto, seed:N, explicit | `window.screenX/screenY` (headless mode only). |
| `--fingerprint-media-features=<scheme,motion,contrast,colors,gamut>` | auto, seed:N, explicit | CSS `matchMedia('(prefers-color-scheme: …)')`, `(color-gamut: …)`, `(prefers-reduced-motion: …)`, `(prefers-contrast: …)`, `(forced-colors: …)`. |
| `--fingerprint-media=<mics,webcams,speakers>` | auto, seed:N, explicit | `navigator.mediaDevices.enumerateDevices()` per-kind counts. Pre-permission state collapses any non-zero count to one entry per kind. |
| `--fingerprint-history-length=<int>` | auto, seed:N, explicit | `history.length`. Derive range `[1, 5]`. |
| `--fingerprint-text-rendering=gamma:<float>,contrast:<float>` | explicit only | Skia `text_gamma` / `text_contrast` overrides (Windows). Retained for experimentation; no `auto`/`seed:N` support. |

</details>

<details>
<summary><b>Proxy-derived and utility switches</b></summary>

These don't fit the seed model. Pass a literal value or omit. Set them to match whatever proxy or VPN exit you're using. A fingerprint that claims `America/New_York` while your traffic exits in Frankfurt is more identifying than no spoofing at all.

| Switch | Modes | Effect |
|---|---|---|
| `--fingerprint-timezone=<IANA>` | explicit only | ICU timezone override (e.g. `America/New_York`). |
| `--fingerprint-geolocation=<lat,lon,acc>` | explicit only | `navigator.geolocation.getCurrentPosition()` override. |
| `--webrtc-ip4=<ip>` | explicit only | WebRTC ICE-candidate IPv4 + SDP override. |
| `--webrtc-ip6=<ip>` | explicit only | WebRTC ICE-candidate IPv6 + SDP override. |
| `--fingerprint-accept-language=<BCP-47>` | explicit only | Forces the HTTP `Accept-Language` header (no effect when a font bundle is active, since the bundle owns the header). |

| Switch | Modes | Effect |
|---|---|---|
| `--auto-decline-webauthn` | presence-only | Auto-rejects WebAuthn/passkey prompts with `NOT_ALLOWED_ERROR` after a randomized 1–5 s delay. Intended for automated runs where no authenticator is attached and a hanging prompt would stall the session. |
| `--show-cdp-cursor` | presence-only | Renders the CDP-driven cursor overlay when DevTools is connected. Useful for visual automation debugging. |

</details>

## Automation: custom CDP methods

Five commands extend the standard Chrome DevTools Protocol, aimed at browser automation and UI testing. Some collapse per-event round-trip latency into a single call; others expose page state standard CDP cannot reach. They're listed in the protocol JSON at `http://127.0.0.1:<port>/json/protocol` and can be invoked through any CDP client (chrome-devtools-frontend, Puppeteer / Playwright via `CDPSession.send(...)`, nodriver / Selenium CDP wrappers, raw WebSocket, etc.).

### `Input.dispatchMousePath`: batched mouse movement

Walks a pre-computed cursor trajectory in a single CDP call instead of N per-segment `Input.dispatchMouseEvent` round-trips. Chromium dispatches the events internally at a fixed `1000 / pollingRateHz` ms interval, so polling rates of 500–1000 Hz become achievable (per-segment CDP round-trip latency normally caps effective rates around 50–100 Hz).

Parameters:
- `path`: array of `{ x: number, y: number }` positions in CSS pixels.
- `pollingRateHz`: integer (e.g. `125`, `500`, `1000`).
- `button`: optional `none` | `left` | `middle` | `right` | `back` | `forward`, default `none`. Held down for the duration of the path. Without it every move is a hover: the compositor starts no drag and grants no pointer capture, so a native control follows the initial press and ignores the rest of the path. Set it to drag, issuing the `mousePressed` and `mouseReleased` around it with `Input.dispatchMouseEvent`.

Returns: nothing. The call completes once the schedule has run.

```json
{
  "method": "Input.dispatchMousePath",
  "params": {
    "path": [{"x": 100, "y": 100}, {"x": 105, "y": 102}, {"x": 110, "y": 105}],
    "pollingRateHz": 500,
    "button": "left"
  }
}
```

### `Input.dispatchKeystrokes`: batched typing with realistic timing

Types a string with variable inter-key timing, optional pauses, and optional typo + correction sequences. The full schedule runs inside the browser process, so per-key round-trip latency is gone: one CDP call per `type()` operation regardless of length.

Parameters:
- `text`: string to type. `\n` maps to Enter.
- `speedMultiplier`: number > 0, default `1.0`. Values > 1 type faster.
- `keystrokeDelayMin` / `keystrokeDelayMax`: integer ms, default `60` / `260`. Inter-keystroke delay range (before speed scaling).
- `keyHoldMin` / `keyHoldMax`: integer ms. keyDown to keyUp hold duration range.
- `contextAware`: bool, default `true`. Applies bigram-frequency and post-punctuation timing adjustments.
- `thinkingPauseProbability`: number 0–1, default `0`. Chance of a longer pause before a character. Pair with `thinkingPauseMin` / `thinkingPauseMax` (integer ms).
- `typoProbability`: number 0–1, default `0`. Chance of injecting a typo + backspace + correction. Realistic values: `0.01`–`0.03`.
- `seed`: number, optional. RNG seed for a deterministic schedule (same params + text + seed produces an identical event sequence), which makes test runs reproducible.

Returns: nothing meaningful. The call blocks until the full schedule has run.

```json
{
  "method": "Input.dispatchKeystrokes",
  "params": {
    "text": "hello world",
    "speedMultiplier": 1.2,
    "typoProbability": 0.02,
    "thinkingPauseProbability": 0.05
  }
}
```

### `DOM.getShadowRoot`: closed shadow root access

Returns the shadow root of a host element regardless of `closed` vs `open` mode. Standard `DOM.describeNode` (even with `pierce: true`) skips closed roots; this command exposes them. Useful for testing pages that encapsulate components behind closed roots, which are otherwise unreachable from an automation harness.

The access is not observable from page JavaScript.

Parameters, exactly one of:
- `nodeId`: integer. The host element's CDP node ID.
- `backendNodeId`: integer. The host element's backend node ID, which is what `Page.captureAgentSnapshot` returns for every element.
- `objectId`: string. A `Runtime.RemoteObjectId` wrapping the host element.

Returns: `{ shadowRoot?: Node }`, the shadow root as a standard CDP Node. The field is omitted when the element has no shadow root. Errors when the node is not an element.

```json
{
  "method": "DOM.getShadowRoot",
  "params": { "nodeId": 42 }
}
```

Once you have the shadow root's `nodeId`, the standard `DOM.querySelector`, `DOM.describeNode`, `DOM.resolveNode`, etc. all work against it.

### `Page.captureAgentSnapshot`: one-call page perception

Returns every interactive element on the page, across cross-origin iframes and both open and closed shadow DOM, with geometry already composed into the root viewport's CSS-pixel space, plus an OOPIF-aggregated screenshot. Replaces the usual accessibility-tree walk and per-frame coordinate math, which costs many round-trips and still misses closed roots and cross-frame occlusion.

Elements that are on-screen, interactive, and unobscured get a short `label` (`"a1"`, `"a2"`) and a distinct outline `color` drawn on the screenshot, so a caller can name a target unambiguously.

Parameters:
- `format`: `png` | `jpeg` | `webp`, default `png`. Screenshot compression format.
- `quality`: integer 0-100, `jpeg`/`webp` only.
- `offscreenMode`: `none` | `summary` | `full`, default `summary`. How to report elements outside the viewport.
- `includeScreenshot`: bool, default `true`.

Returns: `{ url, title, viewport, elements, screenshot?, snapshotToken }`. `viewport` carries its own size, the scroll offsets, the full scrollable size and `deviceScaleFactor`. `snapshotToken` is a cheap change-detection token.

Each element carries `agentNodeId`, `backendNodeId`, `frameId`, `role`, `tag`, `interactive`, `states[]`, its border box (`x`, `y`, `width`, `height`), `inViewport` and `obscured`, plus the following where applicable: `name`, `value`, `description`, `interactiveReason` (`role` | `form-control` | `listener` | `cursor` | `tabindex`), `shadowHostBackendNodeId`, `label`, `color`, `href`, `src`.

```json
{
  "method": "Page.captureAgentSnapshot",
  "params": { "format": "webp", "quality": 80, "offscreenMode": "summary" }
}
```

### `Page.resolveAgentNode`: re-locate a snapshot element

Maps an `agentNodeId` from an earlier `captureAgentSnapshot` back to that element's *current* border box, in the same root-viewport coordinate space. Use it to confirm a target hasn't moved between perception and action without paying for a full re-snapshot. The id is browser-minted and unique across all frames, so it resolves elements in cross-origin iframes too.

Parameters:
- `agentNodeId`: integer from a prior snapshot.

Returns: `{ found, x?, y?, width?, height? }`. `found` is `false` when the id is unknown, or the element no longer exists or isn't laid out.

```json
{
  "method": "Page.resolveAgentNode",
  "params": { "agentNodeId": 17 }
}
```

## Intended use

This is built for people who want control over what their browser discloses: privacy-conscious browsing, security research, testing how your own sites respond to varied client configurations, and automation against systems you own or are authorized to access.

It isn't built for evading bans, operating fake accounts at scale, or circumventing access controls on services you don't own. Those uses tend to violate the terms of service of whatever you're pointing it at, and in some jurisdictions bypassing technical access restrictions carries legal exposure beyond a terms violation. What you do with it is on you.

## Contributing

Bug reports and feature requests are welcome via [Issues](../../issues). Fingerprint-detection reports are especially useful: if a site distinguishes this browser from stock Chrome, open an issue with the site and what gave it away.

## Credits

Built on [Chromium](https://www.chromium.org/). The Safe Browsing removal draws on the [ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium) project's work.

## License

BSD-3-Clause, see [`LICENSE`](LICENSE).

Chromium itself is BSD-3-Clause and bundles components under other licenses; those obligations carry over to this derivative. Third-party notices are listed at `chrome://credits` within the running browser. The curated patches under `patches/ungoogled/` come from [ungoogled-chromium](https://github.com/ungoogled-software/ungoogled-chromium) and [ungoogled-chromium-windows](https://github.com/ungoogled-software/ungoogled-chromium-windows), also BSD-3-Clause.
