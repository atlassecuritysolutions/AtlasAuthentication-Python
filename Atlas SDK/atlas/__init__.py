# Atlas authentication library.
# Get your API key from atlassecurity.site/dashboard.
#
#   import atlas
#   atlas.Startup()
#   if atlas.License.Login("license-key"): pass   # signed in
#
# Namespace layout - pick the right bucket for the job:
#
#   atlas.                       shared/session (Data, Network, Variables, Webhook)
#   atlas.License.               license-key sign-in (headless)
#   atlas.Account.               username+password + email flow (headless)

__version__ = "1.0.0"

from ctypes import byref, c_int
from . import _ffi as _c

_OK = 0


# Your app's API key. Get it from atlassecurity.site/dashboard.
API_KEY = "894kO8WB5suGzk1KuLGoKsZyJPlnUEbYc3LYzZQq8axmgwFZ1rGBMnWzN6Wnjx8q"


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
    """Hard-kill the process via __fastfail. Uncatchable, no cleanup."""
    _c.Exit()


# -- License mode --------------------------------------------------------
# Classic single-user, license-key auth. No email, no verify code.

class License:
    @staticmethod
    def Login(license_key):                      return _c.Login(license_key.encode()) == _OK
    # Username + password sign-in for a license bound to one user (legacy USR mode).
    # For the multi-user flow with email verify, use Atlas.Account.Login.
    @staticmethod
    def LoginUser(username, password):           return _c.LoginUser(username.encode(), password.encode()) == _OK
    # Bind a license key to a new username/password (legacy REG mode).
    # Does NOT sign in on success - call LoginUser(u, p) after.
    @staticmethod
    def Register(license_key, username, password):
        return _c.Register(license_key.encode(), username.encode(), password.encode()) == _OK


# -- Account mode --------------------------------------------------------
# Multi-user (username / password / email) accounts with email verify,
# password reset, and the redeem-a-key-onto-my-account flow.

class Account:
    class Status:
        Ok                 = "Ok"
        WrongCredentials   = "WrongCredentials"
        NeedsVerification  = "NeedsVerification"
        Error              = "Error"

    class LoginResult:
        __slots__ = ("status", "user_id", "error_message",
                     "masked_email", "sign_in_ip", "sign_in_country")
        def __init__(self):
            self.status          = Account.Status.Error
            self.user_id         = 0
            self.error_message   = ""
            self.masked_email    = ""
            self.sign_in_ip      = ""
            self.sign_in_country = ""

    # Sign in with account credentials. Check result.status.
    # On NeedsVerification the SDK holds the challenge - call SubmitVerification(code).
    @staticmethod
    def Login(username, password):
        uid = c_int(0)
        rc = _c.LoginAccountEx(username.encode(), password.encode(), byref(uid))
        r = Account.LoginResult()
        r.user_id = uid.value
        if rc == _OK:
            r.status = Account.Status.Ok
        elif rc == 10:                                 # ATLAS_ERR_NEEDS_VERIFY
            r.status = Account.Status.NeedsVerification
            r.masked_email    = _c.read_str(_c.GetLastVerifyMaskedEmail)
            r.sign_in_ip      = _c.read_str(_c.GetLastVerifyIP)
            r.sign_in_country = _c.read_str(_c.GetLastVerifyCountry)
        elif rc == 3:                                  # ATLAS_ERR_LOGIN_FAILED
            r.status = Account.Status.WrongCredentials
            r.error_message = _c.read_str(_c.GetErrorMessage)
        else:
            r.status = Account.Status.Error
            r.error_message = _c.read_str(_c.GetErrorMessage)
        return r

    # Create a standalone account. Email optional but needed for password reset.
    # Does NOT sign in. If email is set, account stays unverified until ConfirmEmail.
    @staticmethod
    def Register(username, password, email=""):  return _c.RegisterAccount(username.encode(), password.encode(), email.encode()) == _OK
    # Submit the 8-digit code for the pending sign-in verify challenge.
    @staticmethod
    def SubmitVerification(code):                return _c.SubmitVerify(code.encode()) == _OK
    # Resend the sign-in verification code (60s server-side cooldown).
    @staticmethod
    def ResendVerification():                    return _c.ResendVerify() == _OK
    # Confirm a newly-registered account's email with the emailed code.
    @staticmethod
    def ConfirmEmail(code):                      return _c.ConfirmEmail(code.encode()) == _OK
    # True while a registration email-confirm is pending.
    @staticmethod
    def HasPendingEmailConfirm():                return _c.HasPendingEmailConfirm() != 0
    # Redeem a license key onto the currently signed-in account.
    @staticmethod
    def Redeem(license_key):                     return _c.RedeemKey(0, license_key.encode()) == _OK
    # Start a password reset. identifier = username or email.
    # Always returns True - anti-enumeration, the server never leaks whether it matched.
    @staticmethod
    def RequestPasswordReset(identifier):        return _c.RequestPasswordReset(identifier.encode()) == _OK
    # Complete the reset with the emailed code + new password.
    @staticmethod
    def CompletePasswordReset(code, new_password):
        return _c.CompletePasswordReset(code.encode(), new_password.encode()) == _OK


# -- Network -------------------------------------------------------------
# Direct server RPCs on the current session.

class Network:
    # Poll the server to confirm the current session is still valid.
    @staticmethod
    def CheckAuthentication():                   return _c.CheckAuthentication() == _OK
    # Ban the current user from your app. duration_minutes = 0 -> permanent.
    @staticmethod
    def BanUser(reason, duration_minutes=0):     return _c.BanUser(reason.encode(), duration_minutes) == _OK
    # Emit a custom log line (max 512 chars) to the dashboard's Logs tab.
    @staticmethod
    def SubmitLog(text):                         return _c.SubmitLog(text.encode()) == _OK
    # Change the current account's password.
    @staticmethod
    def ChangePassword(old_password, new_password):
        return _c.ChangePassword(old_password.encode(), new_password.encode()) == _OK
    # Round-trip latency to the auth server in ms, or -1 if unreachable.
    @staticmethod
    def Ping():                                  return _c.Ping()


# -- Data ----------------------------------------------------------------
# Read-only session accessors. Populated after a successful sign-in.

class Data:
    # Authentication Data
    @staticmethod
    def GetLicense():           return _c.read_str(_c.GetLicense)
    @staticmethod
    def GetUsername():          return _c.read_str(_c.GetUsername)
    @staticmethod
    def GetEmail():             return _c.read_str(_c.GetEmail)
    @staticmethod
    def GetPassword():          return _c.read_str(_c.GetPassword)
    @staticmethod
    def GetIP():                return _c.read_str(_c.GetIP)
    @staticmethod
    def GetHWID():              return _c.read_str(_c.GetHWID)
    @staticmethod
    def GetDevice():            return _c.read_str(_c.GetDevice)
    @staticmethod
    def GetNote():              return _c.read_str(_c.GetNote)
    @staticmethod
    def GetFirstSeenDate():     return _c.read_str(_c.GetFirstSeenDate)
    @staticmethod
    def GetLastSeenDate():      return _c.read_str(_c.GetLastSeenDate)
    @staticmethod
    def GetUserId():            return _c.GetUserId()
    @staticmethod
    def GetLevel():             return _c.GetLevel()

    # Expiry
    @staticmethod
    def GetExpiry():            return _c.read_str(_c.GetExpiry)
    @staticmethod
    def GetDaysRemaining():     return _c.GetDaysRemaining()
    @staticmethod
    def IsLifetime():           return _c.IsLifetime() != 0
    @staticmethod
    def IsExpiringSoon(days_threshold=7):
        return _c.IsExpiringSoon(days_threshold) != 0

    # Authentication Verdicts
    @staticmethod
    def IsAuthenticated():      return _c.IsAuthenticated() != 0
    @staticmethod
    def IsBanned():             return _c.IsBanned() != 0

    # Global Application Stats
    @staticmethod
    def GetActiveUserCount():   return _c.read_str(_c.GetActiveUserCount)
    @staticmethod
    def GetUserCount():         return _c.read_str(_c.GetUserCount)

    # Atlas Errors
    @staticmethod
    def GetErrorMessage():      return _c.read_str(_c.GetErrorMessage)
    @staticmethod
    def ClearError():           _c.ClearError()
    @staticmethod
    def HasError():             return _c.HasError() != 0


# -- Variables -----------------------------------------------------------
# Read-only key/value store you configure on the dashboard.

class Variables:
    @staticmethod
    def Fetch(key):                              return _c.read_str(_c.VariableFetch, key.encode())
    @staticmethod
    def FetchBool(key):                          return _c.VariableFetchBool(key.encode()) != 0
    @staticmethod
    def FetchInt(key):                           return _c.VariableFetchInt(key.encode())


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
    # POST an arbitrary JSON payload - Slack, custom endpoints, telemetry.
    @staticmethod
    def Send(url, json_payload):
        return _c.WebhookSend(url.encode(), json_payload.encode()) == _OK
