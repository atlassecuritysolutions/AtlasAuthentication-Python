# Atlas SDK — Python binding.
#
#   Dashboard: https://atlassecurity.site/dashboard
#   Docs:      https://atlassecurity.site/docs
#   Legal:     https://atlassecurity.site/legal
#
#   import atlas
#   atlas.API_KEY = "YOUR_API_KEY"
#   atlas.Startup()
#   if atlas.License.Login("license-key"):
#       ...  # signed in
#
# Namespaces:
#   atlas.          session state, data, network, variables, webhooks
#   atlas.License   license-key sign-in
#   atlas.Account   username / password / email accounts

__version__ = "1.0.0"

from ctypes import byref, c_int
from . import _ffi as _c

_OK = 0


# Your app's API key. Get it from atlassecurity.site/dashboard.
API_KEY = "YOUR_API_KEY"


# -- Session lifecycle ---------------------------------------------------

def Startup():
    """Initialise the library. Call once at the top of main()."""
    _c.SetApiKey(API_KEY.encode())
    rc = _c.Startup()
    if rc != _OK:
        raise RuntimeError(_c.read_str(_c.GetErrorMessage) or f"Atlas_Startup failed ({rc})")


def Logout():
    """Terminate the session and clear all authentication state."""
    _c.Logout()


def Exit():
    """Kill the process the hardest way Windows allows. Unbypassable, uncatchable, no cleanup."""
    _c.Exit()


# -- License mode --------------------------------------------------------
# Single-user, license-key auth. No email, no verification code.

class License:
    # License-key sign-in.
    @staticmethod
    def Login(license_key):
        return _c.Login(license_key.encode()) == _OK

    # Username + password sign-in for a license bound to one user.
    # For accounts with email verification, use atlas.Account.Login.
    @staticmethod
    def LoginUser(username, password):
        return _c.LoginUser(username.encode(), password.encode()) == _OK

    # Bind a license key to a new username/password.
    # Does NOT sign in on success — call LoginUser(u, p) after.
    @staticmethod
    def Register(license_key, username, password):
        return _c.Register(license_key.encode(), username.encode(), password.encode()) == _OK


# -- Account mode --------------------------------------------------------
# Username / password / email accounts. Email verification, password reset,
# and per-account key redemption.

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
        __slots__ = ("status", "user_id", "error_message",
                     "expiry", "level", "note",
                     "masked_email", "sign_in_ip", "sign_in_country")
        def __init__(self):
            self.status          = Account.Status.Error
            self.user_id         = 0
            self.error_message   = ""
            self.expiry          = ""
            self.level           = 1
            self.note            = ""
            self.masked_email    = ""
            self.sign_in_ip      = ""
            self.sign_in_country = ""

    # Sign in with account credentials. Check result.status.
    # On NeedsVerification the SDK holds the challenge — call SubmitVerification(code).
    # On Ok, r.expiry / r.level / r.note are populated when the server sent them.
    @staticmethod
    def Login(username, password):
        uid = c_int(0)
        rc = _c.LoginAccountEx(username.encode(), password.encode(), byref(uid))
        r = Account.LoginResult()
        r.user_id = uid.value
        if rc == _OK:
            r.status = Account.Status.Ok
            r.expiry = _c.read_str(_c.GetExpiry)
            r.level  = _c.GetLevel()
            r.note   = _c.read_str(_c.GetNote)
        elif rc == 10:                                 # ATLAS_ERR_NEEDS_VERIFY
            r.status = Account.Status.NeedsVerification
            r.masked_email    = _c.read_str(_c.GetLastVerifyMaskedEmail)
            r.sign_in_ip      = _c.read_str(_c.GetLastVerifyIP)
            r.sign_in_country = _c.read_str(_c.GetLastVerifyCountry)
        elif rc == 3:                                  # ATLAS_ERR_LOGIN_FAILED
            # Server-side reason lives in the message text. The C ABI collapses
            # WrongCredentials / Banned / AccountPaused into one code, so we
            # route on the message; unknown text falls through to WrongCredentials.
            msg = _c.read_str(_c.GetErrorMessage)
            r.error_message = msg
            m = msg.lower()
            if   "banned" in m:                          r.status = Account.Status.Banned
            elif "paused" in m or "account paused" in m: r.status = Account.Status.AccountPaused
            else:                                        r.status = Account.Status.WrongCredentials
        elif rc == 7:                                  # ATLAS_ERR_SERVER
            r.status = Account.Status.ServerUnreachable
            r.error_message = _c.read_str(_c.GetErrorMessage)
        else:
            r.status = Account.Status.Error
            r.error_message = _c.read_str(_c.GetErrorMessage)
        return r

    # Create a standalone account. Email optional but needed for password reset.
    # Does NOT sign in. If email is set, account stays unverified until ConfirmEmail.
    @staticmethod
    def Register(username, password, email=""):
        return _c.RegisterAccount(username.encode(), password.encode(), email.encode()) == _OK

    # Submit the 8-digit code for the pending sign-in verify challenge.
    @staticmethod
    def SubmitVerification(code):
        return _c.SubmitVerify(code.encode()) == _OK

    # Resend the sign-in verification code (60s server-side cooldown).
    @staticmethod
    def ResendVerification():
        return _c.ResendVerify() == _OK

    # Confirm a newly-registered account's email with the emailed code.
    @staticmethod
    def ConfirmEmail(code):
        return _c.ConfirmEmail(code.encode()) == _OK

    # True while a registration email-confirm is pending.
    @staticmethod
    def HasPendingEmailConfirm():
        return _c.HasPendingEmailConfirm() != 0

    # Redeem a license key onto the currently signed-in account.
    @staticmethod
    def Redeem(license_key):
        return _c.RedeemKey(0, license_key.encode()) == _OK

    # Start a password reset. identifier = username or email.
    # Always returns True — anti-enumeration, the server never leaks whether it matched.
    @staticmethod
    def RequestPasswordReset(identifier):
        return _c.RequestPasswordReset(identifier.encode()) == _OK

    # Complete the reset with the emailed code + new password.
    @staticmethod
    def CompletePasswordReset(code, new_password):
        return _c.CompletePasswordReset(code.encode(), new_password.encode()) == _OK


# -- Network -------------------------------------------------------------
# Direct server RPCs on the current session.

class Network:
    # Poll the server to confirm the current session is still valid.
    @staticmethod
    def CheckAuthentication():
        return _c.CheckAuthentication() == _OK

    # Ban the current user from your app. duration_minutes = 0 → permanent.
    @staticmethod
    def BanUser(reason, duration_minutes=0):
        return _c.BanUser(reason.encode(), duration_minutes) == _OK

    # Emit a custom log line (max 512 chars) to the dashboard's Logs tab.
    @staticmethod
    def SubmitLog(text):
        return _c.SubmitLog(text.encode()) == _OK

    # Change the current account's password.
    @staticmethod
    def ChangePassword(old_password, new_password):
        return _c.ChangePassword(old_password.encode(), new_password.encode()) == _OK

    # Round-trip latency to the auth server in ms, or -1 if unreachable.
    @staticmethod
    def Ping():
        return _c.Ping()


# -- Data ----------------------------------------------------------------
# Read-only session accessors. Populated after a successful sign-in.

class Data:
    # Identity
    @staticmethod
    def GetLicense():           return _c.read_str(_c.GetLicense)           # License key the session opened with.
    @staticmethod
    def GetUsername():          return _c.read_str(_c.GetUsername)          # Account username, "" on license-only sessions.
    @staticmethod
    def GetEmail():             return _c.read_str(_c.GetEmail)             # Account email, "" if none / license-only.
    @staticmethod
    def GetPassword():          return _c.read_str(_c.GetPassword)          # Password used at sign-in, "" on license-only.
    @staticmethod
    def GetIP():                return _c.read_str(_c.GetIP)                # Server-detected client IP.
    @staticmethod
    def GetHWID():              return _c.read_str(_c.GetHWID)              # Hardware fingerprint.
    @staticmethod
    def GetDevice():            return _c.read_str(_c.GetDevice)            # ComputerName / Windows username.
    @staticmethod
    def GetNote():              return _c.read_str(_c.GetNote)              # Admin-set note, "" if none.
    @staticmethod
    def GetFirstSeenDate():     return _c.read_str(_c.GetFirstSeenDate)     # First-ever authentication timestamp.
    @staticmethod
    def GetLastSeenDate():      return _c.read_str(_c.GetLastSeenDate)      # Most recent authentication timestamp.
    @staticmethod
    def GetUserId():            return _c.GetUserId()                       # Account row id, 0 if signed out.
    @staticmethod
    def GetLevel():             return _c.GetLevel()                        # Access level, 0 if unknown.

    # Expiry
    @staticmethod
    def GetExpiry():            return _c.read_str(_c.GetExpiry)            # "DD-MM-YYYY HH:MM:SS" or "Lifetime".
    @staticmethod
    def GetDaysRemaining():     return _c.GetDaysRemaining()                # -1 = lifetime, 0 = expired.
    @staticmethod
    def IsLifetime():           return _c.IsLifetime() != 0                 # True if the license never expires.
    @staticmethod
    def IsExpiringSoon(days_threshold=7):                                   # True if expiring within days_threshold.
        return _c.IsExpiringSoon(days_threshold) != 0

    # Status
    @staticmethod
    def IsAuthenticated():      return _c.IsAuthenticated() != 0            # True if a live session is open.
    @staticmethod
    def IsBanned():             return _c.IsBanned() != 0                   # True if the current user is banned.

    # App-wide stats
    @staticmethod
    def GetActiveUserCount():   return _c.read_str(_c.GetActiveUserCount)   # Users currently authenticated app-wide.
    @staticmethod
    def GetUserCount():         return _c.read_str(_c.GetUserCount)         # Total registered users.

    # Errors
    @staticmethod
    def GetErrorMessage():      return _c.read_str(_c.GetErrorMessage)      # Last error message, "" if none.
    @staticmethod
    def ClearError():           _c.ClearError()                             # Reset the error state.
    @staticmethod
    def HasError():             return _c.HasError() != 0                   # True if the last call set an error.


# -- Variables -----------------------------------------------------------
# Read-only key/value store you configure on the dashboard.

class Variables:
    @staticmethod
    def Fetch(key):             return _c.read_str(_c.VariableFetch, key.encode())  # "" if the key doesn't exist.
    @staticmethod
    def FetchBool(key):         return _c.VariableFetchBool(key.encode()) != 0      # "true" / "1" / "yes" → True; else False.
    @staticmethod
    def FetchInt(key):          return _c.VariableFetchInt(key.encode())            # 0 if missing or unparseable.


# -- Webhook -------------------------------------------------------------
# Fire-and-forget HTTP POSTs (Discord, Slack, custom). Unrelated to Atlas auth.

class Webhook:
    # Plaintext Discord webhook message.
    @staticmethod
    def SendDiscord(webhook_url, message):
        return _c.WebhookSendDiscord(webhook_url.encode(), message.encode()) == _OK

    # Discord embed. color is 0xRRGGBB.
    @staticmethod
    def SendDiscordEmbed(webhook_url, title, description, color=0x3498db):
        return _c.WebhookSendDiscordEmbed(webhook_url.encode(), title.encode(), description.encode(), color) == _OK

    # POST an arbitrary JSON payload — Slack, custom endpoints, telemetry.
    @staticmethod
    def Send(url, json_payload):
        return _c.WebhookSend(url.encode(), json_payload.encode()) == _OK
