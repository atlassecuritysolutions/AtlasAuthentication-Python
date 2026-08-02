# Atlas Authentication — Python SDK

![Platform](https://img.shields.io/badge/platform-Windows%20x64-0078D6?logo=windows&logoColor=white) ![Language](https://img.shields.io/badge/language-Python-3776AB?logo=python&logoColor=white) ![License](https://img.shields.io/badge/license-proprietary-lightgrey)

[atlassecurity.site](https://atlassecurity.site) · [Dashboard](https://atlassecurity.site/dashboard) · [Docs](https://atlassecurity.site/docs) · [Discord](https://discord.gg/EG5dmpFaCF) · [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

Most auth libraries stop caring once login succeeds — the client is trusted for the rest of the session. Atlas doesn't. After `Login` returns, the SDK keeps proving to the server that the process is still the one that logged in: same binary, same memory, same network stack, still alive. If any of that stops being true, the process dies. Built for teams whose licensing keeps getting bypassed and whose binaries keep getting cracked.

Two calls get you there:

```python
atlas.Startup()
atlas.License.Login(key)
```

---

## Contents

- [Repo layout](#repo-layout)
- [Prerequisites](#prerequisites)
- [Get an account, an app, a license](#get-an-account-an-app-a-license)
- [Console example](#console-example)
- [Integrate into your project](#integrate-into-your-project)
- [API reference](#api-reference)
  - [Session lifecycle](#session-lifecycle)
  - [`atlas.License`](#atlaslicense)
  - [`atlas.Account`](#atlasaccount)
  - [`atlas.Data`](#atlasdata)
  - [`atlas.Network`](#atlasnetwork)
  - [`atlas.Variables`](#atlasvariables)
  - [`atlas.Webhook`](#atlaswebhook)
- [What Login starts](#what-login-starts)
- [The API-key model](#the-api-key-model)
- [Troubleshooting](#troubleshooting)
- [IMPORANT - Atlas Diagnostic Logs](#diagnostic-logs)
- [Support](#support)
- [Legal](#legal)

---

## Repo layout

```
Python Integration/
├── Atlas SDK/
│   ├── Atlas.dll                  the DLL that runs the protection stack
│   ├── Atlas.c.h                  plain-C header describing the DLL ABI
│   ├── pyproject.toml             build config (setuptools)
│   └── atlas/
│       ├── __init__.py            the binding — mirrors the C++ namespace 1:1
│       ├── _ffi.py                ctypes signatures for every Atlas_* export
│       └── py.typed               PEP 561 marker for type checkers
└── Console Example/
    ├── Atlas Auth Example.py      the star of the show
    ├── build_exe.spec             PyInstaller spec for a single-file .exe
    └── build_exe.bat              one-shot build script
```

`Atlas.dll` is prebuilt and versioned with the release. You don't rebuild the SDK to use it. The Atlas SDK source code is private.

---

## Prerequisites

| | |
|---|---|
| Windows 10 or 11 (x64) | Atlas is Windows-x64 only. |
| [Python 3.9+ (x64)](https://www.python.org/downloads/) | 32-bit Python cannot load `Atlas.dll`. |
| pip | Bundled with Python — installs the SDK wheel. |
| An Atlas account | [atlassecurity.site](https://atlassecurity.site) — free. |

No `pip install` beyond the SDK itself — the binding is pure ctypes, and the DLL ships alongside the package.

---

## Get an account, an app, a license

1. Sign up at [atlassecurity.site](https://atlassecurity.site), verify your email.
2. **Applications → New application** — name it as you like, this will be often shown to end users in MessageBoxes or Emails, Copy the **API key** it hands you.
3. **Licenses → Generate** — pick a duration (Weekly / Monthly / Lifetime / custom), a level (`1` for basic, `2+` for tiered), and optionally a note. Copy the key.
4. *(Optional, for the account flow)* **Applications → Account policy** — choose when verification codes fire (never / first login / every N / once per day / new HWID / new HWID or IP / always). Toggle "email required at registration" if you want to force email addresses.

Free tier: 3 applications, 300 licenses across them, 3 file uploads per app.

---

## Console example

Covers all three auth paths.

1. Open [`Console Example/Atlas Auth Example.py`](Console%20Example/Atlas%20Auth%20Example.py). Replace `"YOUR_API_KEY"` with your key. Save.
2. Run it:
   ```
   python "Console Example/Atlas Auth Example.py"
   ```

The example asks which auth path to try:

```
Atlas Authentication Example

Choose an auth path:
  [1] License key       (classic license authentication)
  [2] Account sign-in   (username + password + email verification)
  [3] Register account  (creates a new account, optional email)

Choice [1/2/3]:
```

Pick `[1]`, paste your license key. On success:

```
--- User Information ---
License:      ATLAS-A9F2K-4RMXM
Expiry:       15-08-2026 14:32:00
IP:           45.11.42.187
HWID:         Atlas-4A9C...E1B2
Level:        1
Note:         None
Active Users: 1
Total Users:  3
```

Open the dashboard **Logs** tab — the login is there with IP, HWID, latency, and result `ALLOW`. From **Sessions → Kick**, terminate the session; the example exits within about five seconds.

Pick `[2]` for the account flow — if the server asks for verification, an 8-digit code arrives by email and the example prompts for it inline. Pick `[3]` to register a new account.

Full source: [`Console Example/Atlas Auth Example.py`](Console%20Example/Atlas%20Auth%20Example.py).

To package as a single-file Windows `.exe`:

```
cd "Console Example"
build_exe.bat
```

PyInstaller bundles the interpreter, the `atlas/` package, and `Atlas.dll` into one exe. Ships as-is on a Windows machine.

---

## Integrate into your project

1. Copy the [`Atlas SDK/`](Atlas%20SDK/) folder into your project (a `vendor/atlas/` folder is conventional), or `pip install .` from that folder to install the wheel.
2. Set your API key from your own code before `Startup()`, or leave it inline in `Atlas SDK/atlas/__init__.py`:
   ```python
   import atlas
   atlas.API_KEY = os.environ["ATLAS_KEY"]
   atlas.Startup()
   ```
3. Wire it up:
   ```python
   import atlas, sys

   atlas.API_KEY = "YOUR_API_KEY"
   atlas.Startup()

   key = prompt_user_for_license()
   if not atlas.License.Login(key):
       print(atlas.Data.GetErrorMessage())
       sys.exit(1)

   run_my_application()   # authenticated
   ```

Once you have a shipping build, compute its SHA-256 and paste it into **Applications → Executable-hash whitelist**. Modified copies are then rejected server-side before the license is even checked. You can whitelist one hash per release and revoke old ones from the same panel.

For PyInstaller `.exe` builds, whitelist the hash of your final `.exe` (from `dist/`), not `python.exe`. If you load Atlas from an unusual location, set `ATLAS_DLL_PATH` in the environment before importing the module:

```python
import os
os.environ["ATLAS_DLL_PATH"] = r"C:\path\to\Atlas.dll"
import atlas
```

The package ships with `py.typed` (PEP 561) — type checkers pick up the signatures automatically. No stub package needed.

---

## API reference

Full API surface in [`Atlas SDK/atlas/__init__.py`](Atlas%20SDK/atlas/__init__.py).

### Session lifecycle

Every integration touches these four calls, regardless of auth path.

```python
atlas.API_KEY = "YOUR_API_KEY"     # set before Startup, or leave inline in __init__.py
atlas.Startup()                    # call once at the top of main()
atlas.Logout()                     # end the session, clear all state
atlas.Exit()                       # kill the process the hardest way Windows allows
```

### `atlas.License`

License-key sign-in: single-user, hardware-bound, no email or verification code.

```python
atlas.License.Login(license_key)                   # key only, HWID-bound
atlas.License.LoginUser(username, password)        # for a license bound to one user
atlas.License.Register(license_key,                # bind an existing license to
                       username, password)         # a new user (does NOT sign in)
```

**`Login` return value and side effects**

| | |
|---|---|
| Returns `True` | License valid, HWID accepted (or first-seen and now bound), session established. |
| Returns `False` | See `atlas.Data.GetErrorMessage()` — invalid key, expired, banned, HWID mismatch, executable-hash mismatch, or server unreachable. |
| On success | Starts the heartbeat and integrity threads (see [What Login starts](#what-login-starts)); populates `atlas.Data`. |
| On failure | No threads started; no partial session state left behind. |

### `atlas.Account`

Username, password, and email accounts, with 8-digit email verification, password reset, and license redemption. Whether a verification code is required on a given sign-in is controlled per-app in the dashboard.

```python
# Inspect r.status to drive your flow.
r = atlas.Account.Login(username, password)
atlas.Account.Register(username, password, email)    # email optional; needed for reset
atlas.Account.SubmitVerification(code)               # 8-digit sign-in code
atlas.Account.ResendVerification()                   # 60 s cooldown
atlas.Account.ConfirmEmail(code)                     # for a pending registration
atlas.Account.HasPendingEmailConfirm()
atlas.Account.Redeem(license_key)                    # add a license to the signed-in account
atlas.Account.RequestPasswordReset(identifier)       # always returns True (anti-enumeration)
atlas.Account.CompletePasswordReset(code, new_pass)
```

`atlas.Account.Status` is one of `Ok`, `WrongCredentials`, `NeedsVerification`, `Banned`, `AccountPaused`, `ServerUnreachable`, `Error`.

- On `Ok` — `r.expiry`, `r.level`, `r.note` are populated.
- On `NeedsVerification` — the server emailed an 8-digit code; pass it to `SubmitVerification`. `r.masked_email`, `r.sign_in_ip`, `r.sign_in_country` are populated so you can render something like "we sent a code to a•••@example.com from Riyadh."

### `atlas.Data`

Session state, valid once `Login` succeeds.

```python
# Identity
GetLicense()  GetUsername()  GetEmail()  GetIP()  GetHWID()  GetDevice()
GetNote()  GetUserId()  GetLevel()
GetFirstSeenDate()  GetLastSeenDate()

# Expiry
GetExpiry()  GetDaysRemaining()  IsLifetime()  IsExpiringSoon(days_threshold=7)

# Status
IsAuthenticated()  IsBanned()

# App-wide counts
GetActiveUserCount()  GetUserCount()

# Errors
GetErrorMessage()  HasError()  ClearError()
```

### `atlas.Network`

Server operations that act on the current session.

```python
CheckAuthentication()                          # force a fresh server round-trip
BanUser(reason, duration_minutes)              # duration = 0 → permanent
SubmitLog(text)                                # ≤ 512 chars, appears in dashboard Logs
ChangePassword(old_password, new_password)     # account flow only
Ping()                                         # round-trip ms to the auth server, -1 if unreachable
```

### `atlas.Variables`

Configuration values set from the dashboard and read at runtime — change them without a rebuild.

```python
atlas.Variables.Fetch("welcome_msg")           # "" if the key doesn't exist
atlas.Variables.FetchBool("beta_feature")      # "true" / "1" / "yes" → True; else False
atlas.Variables.FetchInt("max_items")          # 0 if missing or unparseable
```

### `atlas.Webhook`

Fire-and-forget HTTP POSTs, unrelated to authentication — a convenience for shipping Discord notifications and generic webhooks from your app.

```python
atlas.Webhook.SendDiscord(webhook_url, message)
atlas.Webhook.SendDiscordEmbed(webhook_url, title, description, color)  # color = 0xRRGGBB
atlas.Webhook.Send(url, json_payload)
```

---

## What Login starts

`Login` doesn't end at the handshake. From that point forward, every assumption gets re-verified for the entire life of the session — nothing is trusted just because it was true a moment ago. This is zero trust applied to the client itself, not just the connection.

- **The server re-authenticates the session continuously, not once.** Every check the client passed at login runs again, on a loop, for as long as the process is alive. Passing once buys you nothing later — you keep proving it.
- **Every message between client and server is signed, fresh, and single-use.** Nothing is replayable. A captured request, however perfectly captured, is worthless the moment it's reused.
- **The server holds full control over every live session, in real time.** It can end, message, or re-verify any session on demand — the client has no ability to resist, delay, or negotiate.
- **The binary and its runtime state are continuously verified against what was there at login.** Any modification, any injected code, any external interference with the running process is treated as a compromise — not logged, not flagged, acted on.
- **Detection never announces itself.** No dialog, no error, no exception, nothing to hook or intercept. The response to a failed check is the process ending — not a message telling an attacker what they tripped.
- **Nothing static ever sits in the client waiting to be stolen.** No reusable secret, no long-lived token, no single value that unlocks the next session if it leaks.

This is the actual model: authentication isn't a gate the client passes through once. It's a relationship the server keeps re-verifying, continuously, until the session ends — on the server's terms, not the client's.

---

## The API-key model

The API key is a **routing identifier** — it tells the server which dashboard account and application a request belongs to. It is not what authenticates a request. That rests on:

1. An X25519 handshake, deriving a fresh HMAC key per session.
2. The Ed25519 signature the server places on its handshake reply, verified against three keys pinned inside `Atlas.dll` (primary, backup, emergency). A nulled server can't produce these signatures.
3. HWID binding — the session key is derived with the HWID mixed in, so a stolen session token doesn't work from a different machine.
4. A per-request nonce — replays are dropped.
5. The executable-hash whitelist, if you've configured one.

> [!IMPORTANT]
> A leaked API key alone doesn't let an attacker impersonate a user — but treat it as sensitive. Rotate it on suspected exposure (**Settings → Reset API Key**) and keep it out of public source.

---

## Troubleshooting

**`OSError: [WinError 193] %1 is not a valid Win32 application`** — you're running 32-bit Python against the 64-bit `Atlas.dll`. Install 64-bit Python.

**`FileNotFoundError: Could not find module 'Atlas.dll'`** — the binding probes the SDK folder, PyInstaller `_MEIPASS`, and the folder next to the exe. Set `ATLAS_DLL_PATH` to a fully-qualified path if you load Atlas from somewhere unusual.

**Python exits silently on `Startup()`** — an integrity check tripped the kill path. Dashboard **Logs** shows the reason. Common causes: API key still `"YOUR_API_KEY"`; API key belongs to a deleted app; a debugger is attached (PyCharm debugger, `pdb`, VS Code Python debugger).

**`Login()` returns `False`, "Executable hash mismatch"** — you whitelisted a hash and then rebuilt. Update the whitelist, or don't whitelist during active development.

**`Login()` returns `False`, "License banned" / "HWID banned"** — check **Bans** in the dashboard.

**PyInstaller exe quits immediately** — almost always: `Atlas.dll` isn't bundled, or the apphash is auto-detecting `python.exe` because the spec file didn't include the DLL. Verify with `pyinstaller --log-level=DEBUG` that `Atlas.dll` is listed in the collected binaries.

Full FAQ: [atlassecurity.site/docs](https://atlassecurity.site/docs).

---

## Diagnostic logs

> [!IMPORTANT]
> Every session-ending event — a failed integrity check, a lost connection, a server-issued end to the session — is written to disk the moment it occurs, with the exact cause, source file, and line. The `logs\` folder itself always exists, on every machine running an Atlas-built application, end users included.

Press **`Win + R`**, paste:

```
%LOCALAPPDATA%\AtlasAuth
```

Each entry in `logs\` is a complete record of one event:

```
[Atlas Exit Report]
Time:   2026-08-02 8:20:50
Reason: CheckAuthentication: not authenticated or no session
File:   Atlas Auth.cpp
Line:   2258
```

> [!NOTE]
> The rest of `%LOCALAPPDATA%\AtlasAuth` — `installed.flag`, `declined.flag`, `commit.sha`, `manage_autoupdate.bat` — is dev-only. Those files exist to drive the MSBuild auto-update hook and only appear when a dev environment (Visual Studio, VS Code, MSBuild, JetBrains, and similar) is detected. `logs\` is the only part of this folder your end users will ever have. Always remember to check this folder to diagnose any issues, it is your #1 GOTO!

---

## Support

- **Docs** — [atlassecurity.site/docs](https://atlassecurity.site/docs)
- **Discord** — [discord.gg/EG5dmpFaCF](https://discord.gg/EG5dmpFaCF) (fastest response)
- **Email** — [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

Bug reports: include your OS version, Python version, the failing SDK call, and the dashboard **Logs** entry if there is one.

The DLL's source isn't distributed with this repo. If you need a custom build or believe you've found a bug in `Atlas.dll` itself, contact support — the binding in this repo is thin; the protection stack lives in the DLL.

---

## Legal

© 2025–2026 Atlas Security Solutions. All rights reserved.
Sold by Atlas Security Solutions — Jeddah, Kingdom of Saudi Arabia.

This SDK is licensed, not sold, for one purpose: integrating Atlas Authentication into your own software. That is the entire grant. Nothing here implies any broader right.

**Not permitted, under any circumstance, without Atlas's prior written consent:**
- Reverse engineering, decompiling, disassembling, or otherwise deriving source code, protocols, or algorithms from Atlas binaries, clients, or infrastructure
- Circumventing, disabling, or interfering with any authentication or anti-tamper mechanism
- Accessing, probing, or testing Atlas servers, databases, or infrastructure outside normal SDK operation
- Using knowledge of Atlas internals to build, assist, or distribute a competing product or a bypass tool

A violation terminates this license the moment it occurs. No warning. No cure period.

This agreement is governed by the laws of the Kingdom of Saudi Arabia, including the Anti-Cyber Crime Law (Royal Decree No. M/17, 1428H), Articles 3 and 5. Unauthorized access to Atlas infrastructure is independently a criminal matter in most jurisdictions Atlas operates in, including under the U.S. Computer Fraud and Abuse Act (18 U.S.C. § 1030) and EU Directive 2013/40/EU. Atlas is not confined to one jurisdiction's remedies and will pursue violators wherever they are found.

Atlas monitors for unauthorized access and reverse-engineering activity as a matter of course. Confirmed violations are referred for civil action, criminal referral where warranted, and pursuit of injunctive relief, damages, and cross-border enforcement — without prior notice.

All rights not expressly granted are reserved.

Authorized inquiries only: [mail@atlassecurity.site](mailto:mail@atlassecurity.site) · [atlassecurity.site/legal](https://atlassecurity.site/legal)
