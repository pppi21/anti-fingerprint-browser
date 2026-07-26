# Anti-fingerprint Browser

A Chromium-derived browser with anti-fingerprinting. Made this for personal use but making public for feedback/stars. This guide is AI so there may be mistakes. Credit to the writers of chromium as well as the ungoogled-chromium project for helping with the removal of safebrowsing. Feedback and feature requests are appreciated.
## Install

Two ways to run it — an installer or a portable zip. Both are the same browser;
the installer just handles setup and Windows integration for you.

### Installer (recommended)

1. Download `AntiFingerprintChromium-Setup-<version>.exe` and run it.
2. Choose an install location (or accept the default) and all-users vs. just-me.
3. It installs the browser, adds Start Menu / desktop shortcuts, and registers
   it with Windows as a web browser.
4. To make it your default: tick **"Choose … as your default browser"** on the
   last wizard page, or later open **Settings → Apps → Default apps**, find
   **Anti-Fingerprint Chromium**, and set it for `http`, `https`, and `.html`.
   (Windows only lets *you* pick the default — no app can force it.)

Uninstall from **Settings → Apps** like any normal program.

### Portable (zip)

1. Extract the zip anywhere and run `chrome.exe` — no installation required.
2. *(Optional)* To make the portable copy selectable as your default browser,
   run the included `register-browser.ps1` from the extracted folder in an
   **elevated** PowerShell (or add `-PerUser` to register for just your account,
   no admin needed), then set it in **Settings → Default apps**. Undo any time
   with `register-browser.ps1 -Unregister`.

## Privacy defaults (always on)

A telemetry-off + privacy preset is applied automatically on **every** launch —
no flags or shortcuts needed. It turns off pings, background networking, and
usage/crash reporting, disables Safe Browsing, and **keeps Manifest V2 extension
support enabled** — so uBlock Origin classic (Chrome Web Store or a sideloaded
`.crx`) works as it did pre-Chrome-127.

To launch with stock Chromium behavior instead, add `--use-chromium-defaults`.

## Fingerprint identity — `chrome://nodriver4j-settings`

Fingerprint spoofing is **off by default**. Turn it on at
**`chrome://nodriver4j-settings`**:

- **Off** — no spoofing (standard Chromium fingerprint).
- **Auto** — a fresh random identity each launch.
- **Fixed seed** — a stable identity derived from a number you choose (the same
  number reproduces the same identity across launches).

Your choice is saved and applied on **every** launch, no matter how the browser
is started — a clicked link, a shortcut, or as your default browser. Restart the
browser after changing it. (This is equivalent to the `--fingerprint-seed`
switch below; passing `--fingerprint-seed` on the command line overrides the
saved value for that one launch.)

## Custom command-line switches

Most people won't need these: the privacy defaults are automatic and the
fingerprint identity is set at `chrome://nodriver4j-settings`. The switches
below are for finer control. Pass one by adding it to the **Target** field of
your browser shortcut — it then applies to launches from *that* shortcut only,
while the privacy defaults and the saved fingerprint seed apply to every launch
however the browser is started.

Notation in the **Modes** column: `explicit` means a literal value;
`auto` randomizes once per launch; `seed:N` derives deterministically from
the integer N (same N across two launches → identical values).

The **Master** column indicates whether the switch activates implicitly
when `--fingerprint-seed=auto|<int>` is set with no per-switch override.
Switches marked **—** require explicit opt-in (either an explicit value or
per-switch `auto`/`seed:N`).

---

### Master / preset

| Switch | Modes | Description |
|---|---|---|
| `--fingerprint-seed=auto\|<int>` | auto, integer | Master seed driving every "Master ✓" switch below. `auto` allocates one random seed per launch; `<int>` is reproducible across launches. Usually set persistently via `chrome://nodriver4j-settings` (see above) rather than here; a command-line value overrides the saved one for that launch. |
| `--use-chromium-defaults` | presence-only | Opt out of the always-on browser-defaults preset for this launch — run with stock Chromium behavior. |
| `--browser-defaults` | presence-only | No-op, kept for backward compatibility: the preset it used to enable is now applied by default on every launch (opt out with `--use-chromium-defaults`). |

---

### Fingerprint switches — activate with `--fingerprint-seed`

These derive from the active profile (a coherent identity picked from an
embedded pool) or from pure seed math. All accept per-switch `auto` or
`seed:N` for fine-grained control.

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
| `--nodriver4j-font-bundle=<seed-string>` | auto, seed:N, explicit | ✓ | Selects an on-disk font bundle from `nodriver4j_fonts/`; affects `document.fonts` enumeration and text metric widths. |

---

### Fingerprint switches — NOT activated by `--fingerprint-seed`

These exist but require explicit opt-in. Pass them with `=auto`, `=seed:N`,
or a literal value to use them.

| Switch | Modes | What it spoofs |
|---|---|---|
| `--fingerprint-screen=<w,h,aw,ah,at,cd[,dpr]>` | auto, seed:N, explicit | `screen.width/height/availWidth/availHeight/availTop/colorDepth` plus `window.devicePixelRatio` (optional 7th field). |
| `--fingerprint-screen-position=<x,y>` | auto, seed:N, explicit | `window.screenX/screenY` (headless mode only). |
| `--fingerprint-media-features=<scheme,motion,contrast,colors,gamut>` | auto, seed:N, explicit | CSS `matchMedia('(prefers-color-scheme: …)')`, `(color-gamut: …)`, `(prefers-reduced-motion: …)`, `(prefers-contrast: …)`, `(forced-colors: …)`. |
| `--fingerprint-media=<mics,webcams,speakers>` | auto, seed:N, explicit | `navigator.mediaDevices.enumerateDevices()` per-kind counts. Pre-permission state collapses any non-zero count to one entry per kind. |
| `--fingerprint-history-length=<int>` | auto, seed:N, explicit | `history.length`. Derive range `[1, 5]`. |
| `--audio-noise=<float>` | auto, seed:N, explicit | Per-sample Gaussian noise amplitude for `OfflineAudioContext` rendering. Range `[1e-7, 1e-6]`. |
| `--fingerprint-text-rendering=gamma:<float>,contrast:<float>` | explicit only | Skia `text_gamma` / `text_contrast` overrides (Windows). Retained for experimentation; no `auto`/`seed:N` support. |

---

### Proxy-derived switches — explicit only

These don't fit the seed model. Pass a literal value or omit.

| Switch | Modes | Effect |
|---|---|---|
| `--fingerprint-timezone=<IANA>` | explicit only | ICU timezone override (e.g. `America/New_York`). |
| `--fingerprint-geolocation=<lat,lon,acc>` | explicit only | `navigator.geolocation.getCurrentPosition()` override. |
| `--webrtc-ip4=<ip>` | explicit only | WebRTC ICE-candidate IPv4 + SDP override. |
| `--webrtc-ip6=<ip>` | explicit only | WebRTC ICE-candidate IPv6 + SDP override. |
| `--fingerprint-accept-language=<BCP-47>` | explicit only | Forces the HTTP `Accept-Language` header (no effect when a font bundle is active — the bundle owns the header). |

---

### Other utility switches

| Switch | Modes | Effect |
|---|---|---|
| `--auto-decline-webauthn` | presence-only | Auto-rejects WebAuthn/passkey prompts with `NOT_ALLOWED_ERROR` after a randomized 1–5 s delay (mimics user-cancelled platform-authenticator UI). |
| `--show-cdp-cursor` | presence-only | Renders the CDP-driven cursor overlay when DevTools is connected. Useful for visual automation debugging. |

---

## Custom CDP methods

Three commands extend the standard Chrome DevTools Protocol. They're
listed in the protocol JSON at `http://127.0.0.1:<port>/json/protocol` and
can be invoked through any CDP client (chrome-devtools-frontend,
Puppeteer / Playwright via `CDPSession.send(...)`, nodriver / Selenium
CDP wrappers, raw WebSocket, etc.).

### `Input.dispatchMousePath` — batched human-like mouse movement

Walks a pre-computed cursor trajectory in a single CDP call instead of
N per-segment `Input.dispatchMouseEvent` round-trips. Chromium dispatches
the events internally at a fixed `1000 / pollingRateHz` ms interval so
polling rates of 500–1000 Hz become achievable (per-segment CDP round-
trip latency normally caps effective rates around 50–100 Hz).

Parameters:
- `path` — array of `{ x: number, y: number }` positions in CSS pixels.
- `pollingRateHz` — integer (e.g. `125`, `500`, `1000`).

Returns: `{ x, y }` — the final cursor position.

```json
{
  "method": "Input.dispatchMousePath",
  "params": {
    "path": [{"x": 100, "y": 100}, {"x": 105, "y": 102}, {"x": 110, "y": 105}],
    "pollingRateHz": 500
  }
}
```

### `Input.dispatchKeystrokes` — batched human-like typing

Types a string with realistic timing, optional thinking pauses, and
optional typo + correction sequences. The full schedule runs inside the
browser process so per-key round-trip latency is gone; one CDP call per
`type()` operation regardless of length.

Parameters:
- `text` — string to type. `\n` maps to Enter.
- `speedMultiplier` — number > 0, default `1.0`. Values > 1 type faster.
- `keystrokeDelayMin` / `keystrokeDelayMax` — integer ms, default `60` / `260`. Inter-keystroke delay range (before speed scaling).
- `keyHoldMin` / `keyHoldMax` — integer ms. keyDown → keyUp hold duration range.
- `contextAware` — bool, default `true`. Applies bigram-frequency and post-punctuation timing adjustments.
- `thinkingPauseProbability` — number 0–1, default `0`. Chance of a longer pause before a character. Pair with `thinkingPauseMin` / `thinkingPauseMax` (integer ms).
- `typoProbability` — number 0–1, default `0`. Chance of injecting a typo + backspace + correction. Realistic values: `0.01`–`0.03`.
- `seed` — number, optional. RNG seed for a deterministic schedule (same params + text + seed → identical event sequence).

Returns: nothing meaningful — the call blocks until the full schedule has run.

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

### `DOM.getShadowRoot` — closed shadow root access

Returns the shadow root of a host element regardless of `closed` vs `open`
mode. Standard `DOM.describeNode` (even with `pierce: true`) skips closed
roots; this command exposes them, and page JavaScript cannot detect that
the access happened.

Parameters:
- `nodeId` — integer. The host element's CDP node ID.

Returns: `{ shadowRoot: Node | null }` — the shadow root as a standard CDP Node, or `null` if the element has no shadow root.

```json
{
  "method": "DOM.getShadowRoot",
  "params": { "nodeId": 42 }
}
```

Once you have the shadow root's `nodeId`, the standard `DOM.querySelector`,
`DOM.describeNode`, `DOM.resolveNode`, etc. all work against it.

---

## License

See `LICENSE.txt`. The build is free for personal and commercial use, with
no warranty. Third-party component notices are listed at `chrome://credits`
within the running browser.
