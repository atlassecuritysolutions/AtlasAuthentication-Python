# Atlas SDK — Python

License authentication and continuous binary protection for Windows x64 Python applications. The most complete authentication stack shipping for the Python ecosystem today — verifiable in the header, the DLL, and this repo.

Three calls — `atlas.API_KEY = "your-key"`, `atlas.Startup()`, `atlas.License.Login(key)` — and your process authenticates, keeps verifying itself while it runs, and can be killed live from the dashboard.

---

Most Python auth libraries stop caring after `login()` returns `True`. Atlas doesn't. Login is the easy part; everything after it is what you're actually paying for.

- **Continuous integrity.** A per-session HMAC frame every 5 seconds, a `.text` + IAT recheck every 15, an inline-hook scan on `ws2_32.recv/send/connect` before every frame, and two independent threads checking each other with hardware performance counters. Any failure kills the process through a path with no user-mode handler to catch.
- **Hardware identity from 16 sources.** Firmware serials, TPM key hashes, PCI instance paths, per-device EDIDs — each a separate keyed hash. Spoof one, the other fifteen still ban.
- **Cascade bans.** Ban a license and the engine follows the HWID and IP unions across every account the fingerprint has ever touched, and bans the whole set.
- **Rules engine.** Per-app geofence, two-source anti-VPN (ip-api + proxycheck, cached 6 h), executable-hash whitelist. Cheapest checks first; first catch wins. All of it runs before the license table is opened.
- **Real email layer, built in.** 8-digit codes on new-device sign-ins, registration confirmation, password reset. Seller-branded, with IP / city / country / device on every code. No SMTP to configure.
- **Live control.** Kick sessions, ban HWIDs, push runtime variables without a rebuild. Every login lands in your dashboard **Logs** tab with IP, HWID, latency, and result.
- **Typed and shipped as a wheel.** `atlas/py.typed` marks the package for type checkers; `pyproject.toml` builds a wheel that carries `Atlas.dll` alongside the module.

**Also on the same account: [Atlas Obfuscator](https://atlassecurity.site/obfuscator)** — a Windows PE protector for the binary itself. Control-flow flattening, string encryption, VM-lifted hot paths, anti-debug and anti-dump baked into the output. Sold separately; bundled with Auth in Atlas Complete.

Free forever: 3 apps, 300 licenses across them, 3 file uploads per app. Full security stack, no feature gates. [Plans](https://atlassecurity.site/plans) lifts the caps.

[atlassecurity.site](https://atlassecurity.site) · [Dashboard](https://atlassecurity.site/dashboard) · [Docs](https://atlassecurity.site/docs) · [Legal](https://atlassecurity.site/legal) · [Discord](https://discord.gg/EG5dmpFaCF) · [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

---

## What's in this folder

```
Python Integration/
├── Atlas SDK/
│   ├── Atlas.dll                  the DLL that runs the protection stack
│   ├── Atlas.c.h                  plain-C header describing the DLL ABI
│   ├── pyproject.toml             wheel build config (setuptools)
│   └── atlas/
│       ├── __init__.py            the binding — mirrors the C++ namespace 1:1
│       ├── _ffi.py                ctypes signatures for every Atlas_* export
│       └── py.typed               PEP 561 marker for type checkers
└── Console Example/
    ├── Atlas Auth Example.py      license / account / register / verify
    ├── build_exe.spec             PyInstaller spec for a single-file .exe
    └── build_exe.bat              one-shot build script
```

`Atlas.dll` is prebuilt and versioned with the release. You don't rebuild the SDK to use it.

---

## Prerequisites

- Windows 10 or 11, x64. Atlas is Windows-x64 only — no Linux, macOS, ARM, WSL.
- Python 3.9+ (x64). 32-bit Python cannot load `Atlas.dll`.
- An Atlas account. Sign up at <https://atlassecurity.site>, then **Applications → New application** for an API key and **Licenses → Generate** for a test key (`ATLAS-XXXXX-XXXXX`).

No `pip install` beyond the SDK itself — the binding is pure ctypes, and the DLL ships alongside the package.

---

## Run the Console example

1. Open `Console Example/Atlas Auth Example.py`. Replace `"YOUR_API_KEY"` with your key (or set it inline in `Atlas SDK/atlas/__init__.py`).
2. Run it:
   ```
   python "Console Example/Atlas Auth Example.py"
   ```

The example asks which auth path to try:

```
Atlas Authentication Example

Choose an auth path:
  [1] License key       (single-user, HWID-bound)
  [2] Account sign-in   (username + password + email verification)
  [3] Register account  (create a new account)
```

Pick `[1]`, paste the license. On success:

```
--- User Information ---
License:      ATLAS-A9F2K-4RMXM
Expiry:       15-08-2026 14:32:00
IP:           45.11.42.187
HWID:         Atlas-4A9C...E1B2
Level:        1
Active Users: 1
Total Users:  3
```

The login is in your dashboard **Logs** tab with IP, HWID, latency, and result `ALLOW`. From **Sessions → Kick** you can terminate the session; the example ends within about five seconds.

Whole example is in `Console Example/Atlas Auth Example.py`.

To package as a single-file Windows `.exe`:

```
cd "Console Example"
build_exe.bat
```

PyInstaller bundles the interpreter, the `atlas/` package, and `Atlas.dll` into one exe. Ships as-is on a stock Windows machine.

---

## Integrate into your project

1. Copy the `Atlas SDK/` folder into your project (a `vendor/atlas/` folder is a reasonable place), or `pip install .` from that folder to install the wheel.
2. Set your API key from your own code before `Startup()`, or leave it inline in `Atlas SDK/atlas/__init__.py`:
   ```python
   import atlas
   atlas.API_KEY = os.environ["ATLAS_KEY"]
   atlas.Startup()
   ```
3. Wire it up:
   ```python
   import atlas, sys

   atlas.API_KEY = "your-key"
   atlas.Startup()

   key = prompt_user_for_license()
   if not atlas.License.Login(key):
       print(atlas.Data.GetErrorMessage())
       sys.exit(1)

   run_my_application()   # authenticated
   ```

Once you have a shipping build, compute its SHA-256 and paste it into **Applications → Executable-hash whitelist**. Modified copies get rejected server-side before the license is even checked. Multiple hashes are allowed, one per release.

For PyInstaller `.exe` builds, whitelist the hash of the final `.exe` (from `dist/`), not `python.exe`. If you load Atlas from an unusual location, set `ATLAS_DLL_PATH` in the environment before importing the module:

```python
import os
os.environ["ATLAS_DLL_PATH"] = r"C:\path\to\Atlas.dll"
import atlas
```

---

## API reference

Full surface in `Atlas SDK/atlas/__init__.py`. Summary here.

### Session

```python
atlas.API_KEY = "your-key"     # set before Startup, or leave inline in __init__.py
atlas.Startup()                # call once, at the top of main()
atlas.Logout()                 # end the session, clear all state
atlas.Exit()                   # kill the process the hardest way Windows allows
```

### `atlas.License` — license-key sign-in

```python
atlas.License.Login(key)                                # key only (HWID-bound)
atlas.License.LoginUser(username, password)             # for a license bound to one user
atlas.License.Register(key, username, password)         # bind — does NOT sign in
```

### `atlas.Account` — username / password / email accounts

```python
r = atlas.Account.Login(username, password)             # inspect r.status
atlas.Account.Register(username, password, email)       # email optional; needed for reset
atlas.Account.SubmitVerification(code)                  # 8-digit sign-in code
atlas.Account.ResendVerification()                      # 60s cooldown
atlas.Account.ConfirmEmail(code)                        # for a pending registration
atlas.Account.HasPendingEmailConfirm()
atlas.Account.Redeem(license_key)                       # add a license to the signed-in account
atlas.Account.RequestPasswordReset(identifier)          # always returns True (anti-enumeration)
atlas.Account.CompletePasswordReset(code, new_pass)
```

`atlas.Account.Status` is one of `Ok`, `WrongCredentials`, `NeedsVerification`, `Banned`, `AccountPaused`, `ServerUnreachable`, `Error`. On `NeedsVerification` the server emailed the user an 8-digit code — pass it back through `SubmitVerification`. On `Ok`, `r.expiry` / `r.level` / `r.note` are populated.

### `atlas.Data` — session state, valid after sign-in

```python
# Identity
GetLicense()  GetUsername()  GetEmail()  GetPassword()  GetIP()  GetHWID()  GetDevice()
GetNote()  GetFirstSeenDate()  GetLastSeenDate()  GetUserId()  GetLevel()

# Expiry
GetExpiry()  GetDaysRemaining()  IsLifetime()  IsExpiringSoon(days_threshold=7)

# Status
IsAuthenticated()  IsBanned()

# App-wide
GetActiveUserCount()  GetUserCount()

# Errors
GetErrorMessage()  HasError()  ClearError()
```

### `atlas.Network` — server RPCs on the current session

```python
CheckAuthentication()                          # force a fresh server round-trip
BanUser(reason, duration_minutes)              # duration = 0 → permanent
SubmitLog(text)                                # ≤ 512 chars, shows in Logs
ChangePassword(old_password, new_password)
Ping()                                         # ms to auth server, -1 if unreachable
```

### `atlas.Variables` — server-set config, no rebuild required

```python
atlas.Variables.Fetch("welcome_msg")           # "" if the key doesn't exist
atlas.Variables.FetchBool("beta_feature")      # "true" / "1" / "yes" → True; else False
atlas.Variables.FetchInt("max_items")          # 0 if missing or unparseable
```

### `atlas.Webhook` — fire-and-forget HTTP POSTs (unrelated to Atlas auth)

```python
atlas.Webhook.SendDiscord(webhook_url, message)
atlas.Webhook.SendDiscordEmbed(webhook_url, title, description, color)   # color = 0xRRGGBB
atlas.Webhook.Send(url, json_payload)
```

---

## The API-key model

The API key is a routing identifier. It tells the server which dashboard account the request belongs to. Authentication of each request rests on five things:

1. The X25519 handshake — derives a per-session HMAC key only your app and the server know.
2. The Ed25519 signature the server places on its handshake reply — verified against three keys pinned inside `Atlas.dll` (primary, backup, emergency). A nulled server cannot produce these signatures.
3. The HWID binding — the session key is derived with the HWID mixed in; a stolen session token doesn't work from a different machine.
4. The per-request nonce — replays are dropped.
5. The executable-hash whitelist, if you configured one.

A leaked API key does not by itself let someone impersonate a user. Still, treat it as sensitive: rotate on suspected exposure (**Settings → Rotate key**), keep it out of public source.

In packaged Python apps, never hardcode the API key in a file that ships with the exe. Read it from an env var or a signed remote config at startup.

---

## Troubleshooting

**`OSError: [WinError 193] %1 is not a valid Win32 application`.**
You're running 32-bit Python against the 64-bit `Atlas.dll`. Install 64-bit Python.

**`FileNotFoundError: Could not find module 'Atlas.dll'`.**
The binding probes the SDK folder, PyInstaller `_MEIPASS`, and the folder next to the exe. Set `ATLAS_DLL_PATH` to a fully-qualified path if you load Atlas from somewhere unusual.

**Python exits silently on `Startup()`.**
Integrity check tripped the kill path. Dashboard **Logs** shows the reason. Common: API key still `"YOUR_API_KEY"`, debugger attached (PyCharm debugger, `pdb`, VS Code Python debugger), integrity check tripped.

**`Login()` returns `False`, "Executable hash mismatch".**
You whitelisted an apphash then rebuilt. Update the whitelist, or don't whitelist during active development.

**`Login()` returns `False`, "License banned" / "HWID banned".**
Check **Bans**.

**PyInstaller exe quits immediately.**
Almost always: `Atlas.dll` isn't bundled or the apphash is auto-detecting `python.exe` because the spec file didn't include the DLL. Verify with `pyinstaller --log-level=DEBUG` that `Atlas.dll` is listed in the collected binaries.

Full FAQ: <https://atlassecurity.site/docs>.

---

## Support

<https://atlassecurity.site/docs> · [Discord](https://discord.gg/EG5dmpFaCF) · [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

---

## Legal

© 2025–2026 Atlas Security Solutions. All rights reserved. Sold by Atlas Security Solutions, Jeddah, Kingdom of Saudi Arabia. This SDK exists so developers can integrate Atlas Authentication into their software — if that's you, use it freely.

Prohibited without written authorization: reverse engineering, decompiling, or reconstructing Atlas binaries, protocols, or server infrastructure; tampering with, bypassing, or disabling any authentication or anti-tamper control; probing or interfering with Atlas servers; using knowledge of Atlas internals to build competing platforms or bypass tools. Atlas monitors for unauthorized access and pursues violations under Saudi Arabia Anti-Cybercrime Law (Royal Decree M/17, 1428H, Articles 3–4), the U.S. Computer Fraud and Abuse Act (18 U.S.C. § 1030), EU Directive 2013/40/EU, and WIPO / TRIPS. Remedies include civil action, injunctive relief, and cross-jurisdiction enforcement without prior notice.

Permission requests and legal inquiries: [mail@atlassecurity.site](mailto:mail@atlassecurity.site) · <https://atlassecurity.site/legal>
