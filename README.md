# Atlas Authentication Library - Python

Windows x64 only. Wraps `Atlas.dll` via ctypes; every network op, integrity
check, watchdog, and heartbeat runs inside the DLL - Python only calls in and
reads out. Same security surface as the C++ and JS bindings.

## Install

```sh
pip install .
```

The wheel ships `Atlas.dll` and `Atlas.c.h` next to the package.

## Usage

```python
import atlas

atlas.API_KEY = "your-key"
atlas.Startup()

if atlas.License.Login("ATLAS-XXXXX-XXXXX"):
    print(atlas.Data.GetUsername(), atlas.Data.GetExpiry(), atlas.Data.GetIP())

# Or an account with email verification:
r = atlas.Account.Login("user", "pass")
if r.status is atlas.Account.LoginResult.Status.Ok:
    ...  # signed in
elif r.status is atlas.Account.LoginResult.Status.NeedsVerification:
    print(f"code emailed to {r.masked_email}")
    code = input("Enter the code: ")
    atlas.Account.SubmitVerification(code)

atlas.Network.SubmitLog("hello from python")
atlas.Logout()
```

Full example: `../Console Example/atlas.py`.

## Namespace layout

Mirrors the C++ `Atlas::` layout one-to-one:

| C++                             | Python                          |
|---------------------------------|---------------------------------|
| `Atlas::Startup()`              | `atlas.Startup()`               |
| `Atlas::License::Login(k)`      | `atlas.License.Login(k)`        |
| `Atlas::Account::Login(u,p)`    | `atlas.Account.Login(u,p)`      |
| `Atlas::Account::Register(...)` | `atlas.Account.Register(...)`   |
| `Atlas::Data::GetUsername()`    | `atlas.Data.GetUsername()`      |
| `Atlas::Network::SubmitLog(x)`  | `atlas.Network.SubmitLog(x)`    |
| `Atlas::Variables::Fetch(k)`    | `atlas.Variables.Fetch(k)`      |
| `Atlas::Webhook::SendDiscord()` | `atlas.Webhook.SendDiscord()`   |
| `Atlas::Logout()`               | `atlas.Logout()`                |
| `Atlas::Exit()`                 | `atlas.Exit()`                  |

## DLL discovery

`atlas.Startup()` looks for `Atlas.dll` in this order:

1. `dll_path=` argument to `Startup(dll_path=...)`
2. `ATLAS_DLL_PATH` environment variable
3. `Atlas.dll` next to the installed `atlas/` package

## App-hash pinning

Under a Python host the default apphash is the SHA-256 of `python.exe`, not
your script. Pin it to your entry file or a signed manifest:

```python
atlas.Startup(app_hash_path="dist/my_app.py")
# or, pre-computed:
atlas.Startup(app_hash="<lowercase-hex-sha256>")
```

## Server-driven messages

Dashboard "send message" frames and startup banners render as native Win32
message boxes even from Python - the DLL owns the UI thread. Client-side
startup-failure modals are silenced by default (`quiet=True`); pass
`quiet=False` to `Startup()` to re-enable them.
