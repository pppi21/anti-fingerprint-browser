# NoDriver4j Browser

A Chromium-derived browser with anti-fingerprinting. Made this for personal use but making public for feedback/stars. This guide is AI so there may be mistakes. Credit to the writers of chromium as well as the ungoogled-chromium project for helping with the removal of safebrowsing. Feedback and feature requests are appreciated.
## Quick start

1. Extract the zip anywhere.
2. Right-click `chrome.exe` → **Send to → Desktop (create shortcut)**.
3. Right-click the new shortcut → **Properties**. In the **Target** field,
   append the recommended switches after the path:
   ```
   "C:\path\to\chrome.exe" --browser-defaults --fingerprint-seed=auto
   ```
4. OK. Pin to taskbar if you like. Launching that shortcut starts the
   browser with telemetry off and per-launch fingerprint randomization on.

**uBlock Origin works.** The build keeps Manifest V2 extension support
enabled (via the `--browser-defaults` preset), so installing uBO classic
from the Chrome Web Store or sideloading the `.crx` works as it did
pre-Chrome-127.

## Custom command-line switches

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
| `--fingerprint-seed=auto\|<int>` | auto, integer | Master seed driving every "Master ✓" switch below. `auto` allocates one random seed per launch; `<int>` is reproducible across launches. |
| `--browser-defaults` | presence-only | Expands to a preset of telemetry-off switches and privacy-positive feature flags. User-supplied switches always win; `--enable-features` and `--disable-features` are merged. |

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
