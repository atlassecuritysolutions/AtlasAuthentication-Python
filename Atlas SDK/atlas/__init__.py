"""Atlas SDK - Python binding.

   Dashboard: https://atlassecurity.site/dashboard
   Docs:      https://atlassecurity.site/docs?p=sdk/overview
   Legal:     https://atlassecurity.site/legal

   import atlas
   atlas.API_KEY = "YOUR_API_KEY"
   atlas.Startup()
   if atlas.License.Login("license-key"):
       ...  # signed in

Any call that can fail returns False or an empty value. atlas.Data.GetErrorMessage() says why.

Namespaces:
   atlas.               Startup, Logout, Exit
   atlas.License        sign in with a license key
   atlas.Account        sign in with username + password (+ email)
   atlas.Network        ask the server things during a session
   atlas.Data           read what the session knows
   atlas.Variables      read values you set on the dashboard
   atlas.Entitlements   what this license or account may do
   atlas.Webhook        send an HTTP POST
"""

from ctypes import byref, c_int
from . import _ffi as _c

_OK = 0

# Status codes returned by Account.Login, mirrored from the C ABI.
# Stable, add-only - the binding routes on these without parsing the
# error message unless the code is ATLAS_ERR_LOGIN_FAILED.
_ATLAS_ERR_LOGIN_FAILED = 3
_ATLAS_ERR_SERVER       = 7
_ATLAS_ERR_NEEDS_VERIFY = 10

# Dashboard > Applications. Set before Startup().
API_KEY: str = "YOUR_API_KEY"


# -- Session lifecycle ---------------------------------------------------
# Startup() once, first (raises RuntimeError on failure). Logout() ends the session; the library stays loaded.
# Exit() kills the process, no cleanup.
# https://atlassecurity.site/docs?p=sdk/lifecycle

def Startup() -> None:
    _c.SetApiKey(API_KEY.encode())
    rc = _c.Startup()
    if rc != _OK:
        raise RuntimeError(_c.read_str(_c.GetErrorMessage) or f"Atlas_Startup failed ({rc})")


def Logout() -> None:
    _c.Logout()


def Exit() -> None:
    _c.Exit()


def DisableMessageBoxes(disabled: bool = True) -> None:
    """Stop the library opening any message box of its own. Call it before Startup()."""
    _c.SetQuiet(1 if disabled else 0)


# -- License -------------------------------------------------------------
# Sign in with a license key. The first sign-in locks the key to this PC.
# LoginUser and Register are only for a license that carries its own username and password. For real user accounts use Account.
# https://atlassecurity.site/docs?p=sdk/license

class License:
    @staticmethod
    def Login(license_key: str) -> bool:
        return _c.Login(license_key.encode()) == _OK

    @staticmethod
    def LoginUser(username: str, password: str) -> bool:
        return _c.LoginUser(username.encode(), password.encode()) == _OK

    @staticmethod
    def Register(license_key: str, username: str, password: str) -> bool:
        return _c.Register(license_key.encode(), username.encode(), password.encode()) == _OK


# -- Account -------------------------------------------------------------
# Username and password accounts, with optional email verification and password reset.
# Login returns a result: read result.status first. NeedsVerification means an 8-digit code was emailed, so call SubmitVerification(code).
# Register does not sign in.
# https://atlassecurity.site/docs?p=sdk/account

class Account:
    class Status:
        Ok                = "Ok"
        WrongCredentials  = "WrongCredentials"
        NeedsVerification = "NeedsVerification"
        Banned            = "Banned"
        AccountPaused     = "AccountPaused"
        ServerUnreachable = "ServerUnreachable"
        Error             = "Error"

    class LoginResult:
        __slots__ = (
            "status", "user_id", "error_message",
            "expiry", "level", "note",
            "masked_email", "sign_in_ip", "sign_in_country",
        )

        def __init__(self) -> None:
            self.status          = Account.Status.Error
            self.user_id         = 0
            self.error_message   = ""
            self.expiry          = ""
            self.level           = 1
            self.note            = ""
            self.masked_email    = ""
            self.sign_in_ip      = ""
            self.sign_in_country = ""

    @staticmethod
    def Login(username: str, password: str) -> LoginResult:
        uid = c_int(0)
        rc  = _c.LoginAccountEx(username.encode(), password.encode(), byref(uid))
        r   = Account.LoginResult()
        r.user_id = uid.value

        if rc == _OK:
            r.status = Account.Status.Ok
            r.expiry = _c.read_str(_c.GetExpiry)
            r.level  = _c.GetLevel()
            r.note   = _c.read_str(_c.GetNote)

        elif rc == _ATLAS_ERR_NEEDS_VERIFY:
            r.status          = Account.Status.NeedsVerification
            r.masked_email    = _c.read_str(_c.GetLastVerifyMaskedEmail)
            r.sign_in_ip      = _c.read_str(_c.GetLastVerifyIP)
            r.sign_in_country = _c.read_str(_c.GetLastVerifyCountry)

        elif rc == _ATLAS_ERR_LOGIN_FAILED:
            # C ABI collapses WrongCredentials / Banned / AccountPaused into one
            # code; route on the server's message text. Unknown text falls through
            # to WrongCredentials (the common case).
            msg = _c.read_str(_c.GetErrorMessage)
            r.error_message = msg
            m = msg.lower()
            if "banned" in m:
                r.status = Account.Status.Banned
            elif "paused" in m or "account paused" in m:
                r.status = Account.Status.AccountPaused
            else:
                r.status = Account.Status.WrongCredentials

        elif rc == _ATLAS_ERR_SERVER:
            r.status        = Account.Status.ServerUnreachable
            r.error_message = _c.read_str(_c.GetErrorMessage)

        else:
            r.status        = Account.Status.Error
            r.error_message = _c.read_str(_c.GetErrorMessage)

        return r

    @staticmethod
    def Register(username: str, password: str, email: str = "") -> bool:
        return _c.RegisterAccount(username.encode(), password.encode(), email.encode()) == _OK

    @staticmethod
    def SubmitVerification(code: str) -> bool:
        return _c.SubmitVerify(code.encode()) == _OK

    @staticmethod
    def ResendVerification() -> bool:
        return _c.ResendVerify() == _OK

    @staticmethod
    def ConfirmEmail(code: str) -> bool:
        return _c.ConfirmEmail(code.encode()) == _OK

    @staticmethod
    def HasPendingEmailConfirm() -> bool:
        return _c.HasPendingEmailConfirm() != 0

    @staticmethod
    def Redeem(license_key: str) -> bool:
        return _c.RedeemKey(0, license_key.encode()) == _OK

    @staticmethod
    def RequestPasswordReset(identifier: str) -> bool:
        return _c.RequestPasswordReset(identifier.encode()) == _OK

    @staticmethod
    def CompletePasswordReset(code: str, new_password: str) -> bool:
        return _c.CompletePasswordReset(code.encode(), new_password.encode()) == _OK


# -- Network -------------------------------------------------------------
# Ask the server something during a session. The library already checks the session in the background,
# so CheckAuthentication() is only for right before a sensitive action.
# https://atlassecurity.site/docs?p=sdk/network

class Network:
    @staticmethod
    def CheckAuthentication() -> bool:
        return _c.CheckAuthentication() == _OK

    @staticmethod
    def Download(file_id: int) -> bytes:
        return _c.read_bytes(file_id)

    @staticmethod
    def BanUser(reason: str, duration_minutes: int = 0) -> bool:
        return _c.BanUser(reason.encode(), duration_minutes) == _OK

    @staticmethod
    def SubmitLog(text: str) -> bool:
        return _c.SubmitLog(text.encode()) == _OK

    @staticmethod
    def ChangePassword(old_password: str, new_password: str) -> bool:
        return _c.ChangePassword(old_password.encode(), new_password.encode()) == _OK

    @staticmethod
    def Ping() -> int:
        return _c.Ping()


# -- Data ----------------------------------------------------------------
# Facts about the signed-in session. Valid only after a successful sign-in.
# A getter with nothing to return gives "" or 0. GetDaysRemaining() is the exception: -1 means no expiry,
# 0 means expired or under 24 hours left. GetExpiry() is "DD-MM-YYYY" or "Never".
# https://atlassecurity.site/docs?p=sdk/data

class Data:
    # Identity
    @staticmethod
    def GetLicense() -> str:   return _c.read_str(_c.GetLicense)
    @staticmethod
    def GetUsername() -> str:  return _c.read_str(_c.GetUsername)
    @staticmethod
    def GetEmail() -> str:     return _c.read_str(_c.GetEmail)
    @staticmethod
    def GetPassword() -> str:  return _c.read_str(_c.GetPassword)
    @staticmethod
    def GetIP() -> str:        return _c.read_str(_c.GetIP)
    @staticmethod
    def GetHWID() -> str:      return _c.read_str(_c.GetHWID)
    @staticmethod
    def GetDevice() -> str:    return _c.read_str(_c.GetDevice)
    @staticmethod
    def GetNote() -> str:      return _c.read_str(_c.GetNote)
    @staticmethod
    def GetFirstSeenDate() -> str: return _c.read_str(_c.GetFirstSeenDate)
    @staticmethod
    def GetLastSeenDate() -> str: return _c.read_str(_c.GetLastSeenDate)
    @staticmethod
    def GetUserId() -> int:    return _c.GetUserId()
    @staticmethod
    def GetLevel() -> int:     return _c.GetLevel()

    # Expiry
    @staticmethod
    def GetExpiry() -> str:    return _c.read_str(_c.GetExpiry)
    @staticmethod
    def GetDaysRemaining() -> int: return _c.GetDaysRemaining()
    @staticmethod
    def IsLifetime() -> bool:  return _c.IsLifetime() != 0
    @staticmethod
    def IsExpiringSoon(days_threshold: int = 7) -> bool:
        return _c.IsExpiringSoon(days_threshold) != 0

    # Status
    @staticmethod
    def IsAuthenticated() -> bool: return _c.IsAuthenticated() != 0
    @staticmethod
    def IsBanned() -> bool:    return _c.IsBanned() != 0

    # App-wide stats
    @staticmethod
    def GetActiveUserCount() -> str: return _c.read_str(_c.GetActiveUserCount)
    @staticmethod
    def GetUserCount() -> str: return _c.read_str(_c.GetUserCount)

    # Errors
    @staticmethod
    def GetErrorMessage() -> str: return _c.read_str(_c.GetErrorMessage)
    @staticmethod
    def ClearError() -> None:  _c.ClearError()
    @staticmethod
    def HasError() -> bool:    return _c.HasError() != 0


# -- Variables -----------------------------------------------------------
# Values you set on the dashboard, read while the app runs. Change one without shipping a new build.
# A key that does not exist gives "" (Fetch), 0 (FetchInt) or False (FetchBool).
# https://atlassecurity.site/docs?p=sdk/variables

class Variables:
    @staticmethod
    def Fetch(key: str) -> str:            return _c.read_str(_c.VariableFetch, key.encode())
    @staticmethod
    def FetchBool(key: str) -> bool:        return _c.VariableFetchBool(key.encode()) != 0
    @staticmethod
    def FetchInt(key: str) -> int:         return _c.VariableFetchInt(key.encode())


# -- Entitlements --------------------------------------------------------
# What this license or account may do: the features and credits you create on the dashboard.
# Has and Remaining are for showing and hiding. Only Consume is enforced by the server.
# https://atlassecurity.site/docs?p=sdk/entitlements

class Entitlements:
    @staticmethod
    def Has(key: str) -> bool:
        return _c.EntitlementHas(key.encode()) == 1

    @staticmethod
    def Remaining(key: str) -> int:
        return _c.EntitlementRemaining(key.encode())

    @staticmethod
    def Consume(key: str, amount: int = 1) -> bool:
        return _c.EntitlementConsume(key.encode(), amount) == 1

    @staticmethod
    def List() -> list[str]:
        return [k for k in _c.read_str(_c.EntitlementList).split("\n") if k]

    @staticmethod
    def Refresh() -> bool:
        return _c.EntitlementRefresh() == 1


# -- Webhook -------------------------------------------------------------
# Send an HTTP POST from the client: Discord, Slack or your own endpoint. Unrelated to Atlas sign-in.
# https://atlassecurity.site/docs?p=sdk/webhook

class Webhook:
    @staticmethod
    def SendDiscord(webhook_url: str, message: str) -> bool:
        return _c.WebhookSendDiscord(webhook_url.encode(), message.encode()) == _OK

    @staticmethod
    def SendDiscordEmbed(webhook_url: str, title: str, description: str, color: int = 0x3498db) -> bool:
        return _c.WebhookSendDiscordEmbed(webhook_url.encode(), title.encode(), description.encode(), color) == _OK

    @staticmethod
    def Send(url: str, json_payload: str) -> bool:
        return _c.WebhookSend(url.encode(), json_payload.encode()) == _OK
