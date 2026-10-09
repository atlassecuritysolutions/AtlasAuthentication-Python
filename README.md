# Atlas Authentication - Python SDK

![Platform](https://img.shields.io/badge/platform-Windows%20x64-0078D6?logo=windows&logoColor=white) ![Language](https://img.shields.io/badge/language-Python-3776AB?logo=python&logoColor=white) ![License](https://img.shields.io/badge/license-MIT%20source%20%C2%B7%20proprietary%20DLL-lightgrey)

[atlassecurity.site](https://atlassecurity.site) · [Dashboard](https://atlassecurity.site/dashboard) · [Docs](https://atlassecurity.site/docs) · [Discord](https://discord.gg/EG5dmpFaCF) · [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

**Authorization that holds under active attack.**

Most auth libraries stop caring once login succeeds - the client is trusted for the rest of the session. Atlas doesn't. After `Login` returns, the SDK keeps proving to the server that the process is still the one that logged in: same binary, same memory, same network stack, still alive. If any of that stops being true, the process ends. Built for teams whose licensing keeps getting bypassed and whose binaries keep getting cracked.

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [Get an account, an app, and a license](#get-an-account-an-app-and-a-license)
- [Examples](#examples)
- [API at a glance](#api-at-a-glance)
- [How a session is protected](#how-a-session-is-protected)
- [The API-key model](#the-api-key-model)
- [Executable hash whitelist](#executable-hash-whitelist)
- [Packaging](#packaging)
- [Auto-update](#auto-update)
- [Troubleshooting](#troubleshooting)
- [Diagnostic logs](#diagnostic-logs)
- [Support](#support)
- [License](#license)

## Install

### Requirements

| | |
|---|---|
| Windows 10 or 11 (x64) | Atlas is Windows-x64 only. |
| [Python 3.9+ (x64)](https://www.python.org/downloads/) | 32-bit Python cannot load `Atlas.dll`. |
| pip | Installs the SDK from PyPI. |
| An Atlas account | [atlassecurity.site](https://atlassecurity.site) - free. |

### Add it to your project

```
pip install atlas-auth
```

That installs the binding and `Atlas.dll`. The binding is pure `ctypes` - no compiler, no extra dependencies. Then `import atlas` and set `atlas.API_KEY` before `atlas.Startup()`.

> **1.0.3 and earlier:** the wheel installs `Atlas.dll` at the root of your Python environment (`sys.prefix`), but the binding looked beside `site-packages`. If `import atlas` raises `FileNotFoundError: Atlas.dll not found...`, update, or point the binding at the DLL before importing:
>
> ```python
> import os, sys
> os.environ["ATLAS_DLL_PATH"] = os.path.join(sys.prefix, "Atlas.dll")
> import atlas
> ```

Vendoring instead: copy the `Atlas SDK/` folder into your project and keep `atlas/` and `Atlas.dll` side by side - the binding finds the DLL beside the package with no configuration. Use the PyPI path for normal projects; vendor when the SDK has to ride inside a private package index or an air-gapped build.

### What's in this repo

```
Atlas SDK/
  Atlas.dll                     the DLL that runs the protection stack
  pyproject.toml, setup.py      build config (setuptools)
  atlas/__init__.py             the binding - mirrors the C++ namespace 1:1
  atlas/_ffi.py                 ctypes signatures for every Atlas_* export
  atlas/py.typed                PEP 561 marker: the binding is typed
Console Example/
  Atlas Auth Example.py         headless CLI: license, account and register paths
  build_exe.spec, build_exe.bat PyInstaller spec and one-shot build for a single-file .exe
```

`Atlas.dll` is prebuilt and versioned with the release. You don't rebuild the SDK. The SDK source is private.

## Quick start

```python
import atlas, sys, os

atlas.API_KEY = os.environ["ATLAS_KEY"]
atlas.Startup()

if not atlas.License.Login(os.environ["LICENSE"]):
    print(atlas.Data.GetErrorMessage())
    sys.exit(1)

print("License:", atlas.Data.GetLicense())
atlas.Logout()
```

> **Run without a debugger attached.** An attached debugger is treated as tampering: the process ends shortly after `Startup()`, and the event can be reported against the license or HWID as a ban. In Python: no `pdb`, no VS Code Python debugger, no PyCharm debugger.

## Get an account, an app, and a license

1. Sign up at [atlassecurity.site](https://atlassecurity.site) and verify your email.
2. **Dashboard → Applications → New application.** Name it - end users see the name in dialogs and emails. Copy the **API key**. You can view it again later under **Applications → Manage → View API Key**.
3. **Dashboard → Users → License users → Generate.** Pick a duration (or no expiry), a level (`1` for basic, `2+` for tiered) and an optional note. Copy the key.
4. *Account flow only:* accounts live under **Users → Account users**. **Settings → Security → Account policy** sets when 8-digit verification codes fire (never, first login, every N logins, once per H hours, new device, new device or IP, always) and whether registration requires an email or a license key.

Free tier: 3 applications, 300 licenses per app, 3 file uploads per app.

## Examples

### Console example

Covers all three auth paths.

1. In `Console Example/Atlas Auth Example.py`, replace `"YOUR_API_KEY"` with your key.
2. Run it:

   ```
   python "Console Example/Atlas Auth Example.py"
   ```

The example asks which path to try:

```
Atlas Authentication Example

Choose an auth path:
  [1] License key       (classic, HWID-bound)
  [2] Account sign-in   (username + password + email verification)
  [3] Register account  (creates a new account, optional email (Configured in dashboard))

Choice [1/2/3]:
```

Pick `[1]` and paste a license key. On success:

```
--- User Information ---
License:      ATLAS-A9F2K-4RMXM
Expiry:       15-08-2026
IP:           203.0.113.42
HWID:         Atlas-4A9C...E1B2
Level:        1
Note:         None
Active Users: 1
Total Users:  3
```

Open **Dashboard → Logs** - the login is there with its IP, HWID and result. From **Monitor → Kill**, end the session; the example exits within a few seconds. Pick `[2]` for the account flow - if the server asks for verification, an 8-digit code arrives by email and the example prompts for it inline. Pick `[3]` to register a new account.

To build a single-file `.exe`, see [Packaging](#packaging).

## API at a glance

```python
# Session
atlas.API_KEY = "YOUR_API_KEY"     # set before Startup
atlas.Startup()                    # once; raises RuntimeError on failure
atlas.Logout()                     # end the session, clear all state
atlas.Exit()                       # hard-terminate the process, uncatchable

# License
atlas.License.Login(license_key)                          # key only, HWID-bound
atlas.License.LoginUser(username, password)               # for a license bound to one user
atlas.License.Register(license_key, username, password)   # binds a license; does NOT sign in

# Account
r = atlas.Account.Login(username, password)               # inspect r.status
atlas.Account.Register(username, password, email)         # email optional; needed for reset
atlas.Account.SubmitVerification(code)                    # 8-digit sign-in code
atlas.Account.ResendVerification()                        # 60 s cooldown
atlas.Account.ConfirmEmail(code)                          # for a pending registration
atlas.Account.HasPendingEmailConfirm()
atlas.Account.Redeem(license_key)                         # apply a key to the signed-in account
atlas.Account.RequestPasswordReset(identifier)            # True whether or not it matched
atlas.Account.CompletePasswordReset(code, new_password)

# Network
atlas.Network.CheckAuthentication()                       # force a fresh server round-trip
atlas.Network.Download(file_id)                           # dashboard-uploaded file → bytes, empty on failure
atlas.Network.BanUser(reason, duration_minutes)           # 0 (the default) = permanent
atlas.Network.SubmitLog(text)                             # ≤ 512 chars, shows in Dashboard → Logs
atlas.Network.ChangePassword(old_password, new_password)  # account sessions only
atlas.Network.Ping()                                      # ms to reach the auth server, -1 if unreachable

# Data - valid once Login succeeds
GetLicense()  GetUsername()  GetEmail()  GetPassword()  GetIP()  GetHWID()  GetDevice()
GetNote()  GetUserId()  GetLevel()  GetFirstSeenDate()  GetLastSeenDate()
GetExpiry()  GetDaysRemaining()  IsLifetime()  IsExpiringSoon(days_threshold=7)
IsAuthenticated()  IsBanned()  GetActiveUserCount()  GetUserCount()
GetErrorMessage()  HasError()  ClearError()

# Variables - set on the dashboard, read at runtime, no rebuild
atlas.Variables.Fetch("key");  atlas.Variables.FetchBool("key");  atlas.Variables.FetchInt("key")

# Entitlements (releases after 1.0.3) - named features and counters the seller gives a license or account
atlas.Entitlements.Has("key")                   # held, not expired, and for a counter something left
atlas.Entitlements.Remaining("key")             # -1 no limit, 0 none, else what is left
atlas.Entitlements.Consume("key", 1)            # spend from a counter; False if refused (Data.GetErrorMessage() says why)
atlas.Entitlements.List();  atlas.Entitlements.Refresh()    # keys held; re-read now (the list is cached ~20 s)

# Webhook - fire-and-forget POSTs
atlas.Webhook.SendDiscord(webhook_url, message)
atlas.Webhook.SendDiscordEmbed(webhook_url, title, description, color)   # color = 0xRRGGBB
atlas.Webhook.Send(url, json_payload)
```

The C++ built-in Win32 dialogs are not available in Python - draw your own UI and call the same methods. `atlas.Account.Status` holds the seven status strings below.

`Account.Login` returns a result. Branch on `status` first:

| Status | Meaning | Do |
|---|---|---|
| `Ok` | Signed in. `user_id`, `expiry`, `level`, `note` are populated. | Continue. |
| `NeedsVerification` | The server emailed an 8-digit code. `masked_email`, `sign_in_ip`, `sign_in_country` are populated. | Prompt for the code, then `SubmitVerification(code)`. |
| `WrongCredentials` | Unknown username or password. | Show the message; let the user retry. |
| `Banned` | The account is banned. | Show the message. Lift the ban under **Bans** in the dashboard. |
| `AccountPaused` | Paused by the seller. | Show the message. The seller resumes it from the dashboard. |
| `ServerUnreachable` | Network or DNS failure. On 1.0.3 and earlier this status is not returned: a network failure arrives as `WrongCredentials` with the cause in `error_message`. | Back off and retry. |
| `Error` | Anything else. | Show `error_message`. |

**Good to know**

- `GetExpiry()` is a `DD-MM-YYYY` date (valid through the end of that day) or `Never`. `GetDaysRemaining()` is `-1` with no expiry, `0` when expired or under 24 hours are left, otherwise whole days.
- `GetNote()` is `None` when no note is set.
- On account sessions `GetLicense()` returns `user:<username>`, not a key. Show `GetUsername()` instead.
- `GetPassword()` returns the password used at sign-in, in cleartext, for the life of the session.
- `SubmitLog` queues the line (512 characters max); the next heartbeat sends it.
- `Login` returns `false` on failure. Read `GetErrorMessage()` for the reason: invalid key, expired, banned, HWID mismatch, executable-hash mismatch, or server unreachable. On failure no threads start and no session state is left behind.

Typing: the package ships inline type hints and a `py.typed` marker, so mypy and Pyright check your calls with no stubs. `atlas.Account.Login` returns an `atlas.Account.LoginResult`; the `Status` values are plain strings.

Full reference with signatures and examples in all three languages: [SDK reference](https://atlassecurity.site/docs?p=sdk/lifecycle).

## How a session is protected

`Login` doesn't end at the handshake. From that point forward, every assumption gets re-verified for the entire life of the session - nothing is trusted just because it was true a moment ago. This is zero trust applied to the client itself, not just the connection.

- **The server re-authenticates the session continuously, not once.** Every check the client passed at login runs again, on a loop, for as long as the process is alive. Passing once buys you nothing later - you keep proving it.
- **Every message between client and server is signed, fresh, and single-use.** Nothing is replayable. A captured request, however perfectly captured, is worthless the moment it's reused.
- **The server holds full control over every live session, in real time.** It can end, message, or re-verify any session on demand - the client has no ability to resist, delay, or negotiate.
- **The binary and its runtime state are continuously verified against what was there at login.** Any modification, any injected code, any external interference with the running process is treated as a compromise - not logged, not flagged, acted on.
- **Detection never announces itself.** No dialog, no error, no exception, nothing to hook or intercept. The response to a failed check is the process ending - not a message telling an attacker what they tripped.
- **Nothing static ever sits in the client waiting to be stolen.** No reusable secret, no long-lived token, no single value that unlocks the next session if it leaks.

Heartbeat: license sessions hold a persistent socket and beat every 3-7 s; account sessions poll every 5 s. From the dashboard you can message a live session (**Monitor → Message**), end it (**Monitor → Kill**) or ban the user (**Bans**).

## The API-key model

The API key is a **routing identifier** - it tells the server which dashboard account and application a request belongs to. It is not what authenticates a request. That rests on:

1. An X25519 handshake, deriving a fresh HMAC key per session.
2. The Ed25519 signature the server places on its handshake reply, verified against three keys pinned inside `Atlas.dll` (primary, backup, emergency). A nulled server can't produce these signatures.
3. HWID binding - the session key is derived with the HWID mixed in, so a stolen session token doesn't work from a different machine.
4. A per-request nonce - replays are dropped.
5. The executable-hash whitelist, if you've added any.

> **Important:** a leaked API key alone doesn't let an attacker impersonate a user - but treat it as sensitive. Rotate it on suspected exposure (**Dashboard → Settings → Security → Reset API key**) and keep it out of public source.

## Executable hash whitelist

Once you have a shipping build, drop the `.exe` into **Dashboard → Settings → Security → Authorized binary hashes → Authorize a binary**. The dashboard computes the SHA-256 in your browser - the file never leaves it. Modified copies are then rejected server-side before the license is even checked. Authorize one hash per release; remove old ones from the same panel. Building in CI? Choose **Paste hash** and paste the output of `Get-FileHash "myapp.exe" -Algorithm SHA256`.

Whitelist the hash of the **packaged** `.exe` - the single file PyInstaller produces - not `python.exe`. Run unpackaged (`python app.py`) and every user on the same Python build sends the same hash, so a whitelist entry identifies the interpreter, not your app.

More: [Executable Hash Whitelist](https://atlassecurity.site/docs?p=concepts/hash-whitelist).

## Packaging

**Single-file `.exe` with PyInstaller.** In `Console Example/`:

```
pip install pyinstaller
build_exe.bat
```

`build_exe.bat` wraps `pyinstaller build_exe.spec` with the right flags and writes `Atlas Auth Example (Python).exe` to the `--distpath` folder set in the bat. The spec bundles the interpreter, the `atlas/` package and `Atlas.dll` into that one file with `binaries=[(Atlas.dll, '.')]`; at launch the exe unpacks to a temporary `_MEIxxxxxx` folder and `atlas/_ffi.py` finds the DLL there, so no `ATLAS_DLL_PATH` is needed. To ship the DLL beside the exe instead (revisable without a rebuild), drop the `binaries` entry and copy `Atlas.dll` next to the exe.

The DLL is found in this order: `ATLAS_DLL_PATH`, beside a frozen exe or in its `_MEIPASS` folder, then beside the `atlas/` package.

Other packagers (Nuitka, py2exe) aren't covered by the example. `ATLAS_DLL_PATH`, set before `import atlas`, is the universal fallback.

## Auto-update

Ship a new build without your users doing anything: upload it under **Dashboard → Settings → Security → Versions**, promote it, and every client on an older authorized version replaces its own `.exe` on its next launch. `Startup()` checks before any login, verifies the SHA-256 of the download, swaps the file and relaunches - about two seconds. Rollback is promoting an earlier version. It replaces one file, so it suits single-file builds (a PyInstaller one-file `.exe`). Details: [Auto-Update](https://atlassecurity.site/docs?p=guides/auto-update).

## Troubleshooting

**`FileNotFoundError: Atlas.dll not found. Run from SDK tree, frozen via PyInstaller, or set ATLAS_DLL_PATH.`** - raised at `import atlas`, before `Startup()`. On 1.0.3 and earlier after a `pip install`, see the note under [Install](#add-it-to-your-project). Otherwise verify `Atlas.dll` sits beside the `atlas/` package or the application, or set `ATLAS_DLL_PATH` to its absolute path.

**`OSError: [WinError 193] %1 is not a valid Win32 application`** - you're running a 32-bit Python interpreter. Atlas requires 64-bit Python.

**The app exits shortly after `Startup()`** - Atlas ended the process after a check failed. Verify `atlas.API_KEY` is set, the application still exists in the dashboard, and no debugger is attached (`pdb`, VS Code Python debugger, PyCharm debugger). See [Diagnostic logs](#diagnostic-logs) for the exact reason.

**`Login()` returns `False`** - call `atlas.Data.GetErrorMessage()`. Common causes: an executable-hash mismatch after a rebuild, an expired or banned license, a banned HWID, invalid credentials.

**A packaged app exits immediately** - verify `Atlas.dll` is bundled with the executable, and if you've authorized binary hashes, confirm the packaged exe matches one.

## Diagnostic logs

Every session-ending event - a failed integrity check, a lost connection, a server-issued end to the session - is written to disk the moment it occurs, with the exact cause, source file and line. The `logs\` folder always exists on every machine running an Atlas-built application, end users included.

Press **`Win + R`** and paste:

```
%LOCALAPPDATA%\AtlasAuth
```

Each `atlas_exit_<timestamp>.log` in `logs\` is a complete record of one event:

```
[Atlas Exit Report]
Time:   2026-08-02 08:38:50
Reason: CheckAuthentication: not authenticated or no session
File:   Atlas Auth.cpp
Line:   2258
```

> The rest of that folder is dev-only: `dev_marker.json`, written by the install hook when pip installs from the source distribution. End users only ever have `logs\` and, after a tamper trip, `pending_bans.dat`. Check `logs\` first whenever a process ends unexpectedly.

The reasons, with what causes each: [Diagnostic Logs](https://atlassecurity.site/docs?p=diagnostics/logs).

## Support

- **Docs** - [atlassecurity.site/docs](https://atlassecurity.site/docs)
- **Discord** - [discord.gg/EG5dmpFaCF](https://discord.gg/EG5dmpFaCF) (fastest response)
- **Email** - [mail@atlassecurity.site](mailto:mail@atlassecurity.site)

Bug reports: include your OS version, Python version, the failing SDK call, and the **Dashboard → Logs** entry or the newest `atlas_exit_*.log` if there is one.

The DLL's source isn't distributed with this repo. If you need a custom build, or believe you've found a bug in `Atlas.dll` itself, contact support - the binding in this repo is thin; the protection stack lives in the DLL.

## License

The binding source (`atlas/`) and the example code in this repository are released under the MIT License - see `LICENSE`. Everything below applies to `Atlas.dll`, to Atlas services, and to Atlas internals.

© 2025–2026 Atlas Security Solutions. All rights reserved.
Sold by Atlas Security Solutions - Jeddah, Kingdom of Saudi Arabia.

This SDK is licensed, not sold, for one purpose: integrating Atlas Authentication into your own software. That is the entire grant. Nothing here implies any broader right.

**Not permitted, under any circumstance, without Atlas's prior written consent:**
- Reverse engineering, decompiling, disassembling, or otherwise deriving source code, protocols, or algorithms from Atlas binaries, clients, or infrastructure
- Circumventing, disabling, or interfering with any authentication or anti-tamper mechanism
- Accessing, probing, or testing Atlas servers, databases, or infrastructure outside normal SDK operation
- Using knowledge of Atlas internals to build, assist, or distribute a competing product or a bypass tool

A violation terminates this license the moment it occurs. No warning. No cure period.

This agreement is governed by the laws of the Kingdom of Saudi Arabia, including the Anti-Cyber Crime Law (Royal Decree No. M/17, 1428H), Articles 3 and 5. Unauthorized access to Atlas infrastructure is independently a criminal matter in most jurisdictions Atlas operates in, including under the U.S. Computer Fraud and Abuse Act (18 U.S.C. § 1030) and EU Directive 2013/40/EU. Atlas is not confined to one jurisdiction's remedies and will pursue violators wherever they are found.

Atlas monitors for unauthorized access and reverse-engineering activity as a matter of course. Confirmed violations are referred for civil action, criminal referral where warranted, and pursuit of injunctive relief, damages, and cross-border enforcement - without prior notice.

All rights not expressly granted are reserved.

Authorized inquiries only: [mail@atlassecurity.site](mailto:mail@atlassecurity.site) · [atlassecurity.site/legal](https://atlassecurity.site/legal)
