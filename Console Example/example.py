# Atlas Authentication Library - Example Usage (Console)
# Run as x64 Python 3.9+ on Windows | Set your API key in atlas/__init__.py (atlas.API_KEY)

import sys
from pathlib import Path

# Add the sibling Atlas SDK folder so `import atlas` finds it locally when
# running the raw .py from this checkout. Skipped when frozen (PyInstaller
# bundles the atlas/ package into the exe at build time).
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "Atlas SDK"))

import atlas


def main():
    # Must be called once at startup before any other Atlas functions.
    atlas.Startup()

    print("Atlas Authentication Example\n")
    print("Choose an auth path:")
    print("  [1] License key       (classic, HWID-bound)")
    print("  [2] Account sign-in   (username + password + email verification)")
    print("  [3] Register account  (creates a new account, optional email (Configured in dashboard))")
    print()
    choice = input("Choice [1/2/3]: ").strip()

    authed = False

    if choice == "1":
        license_key = input("Enter license key: ").strip()
        authed = atlas.License.Login(license_key)

    elif choice == "2":
        # ================================================================
        # ACCOUNT SIGN-IN - headless flow, every prompt rendered inline.
        #
        # Account.Login() returns a LoginResult. On NeedsVerification the
        # server emailed an 8-digit code; the SDK is holding the challenge
        # until SubmitVerification(code) is called.
        # ================================================================
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()

        r = atlas.Account.Login(username, password)
        S = atlas.Account.Status

        if r.status == S.Ok:
            authed = True
        elif r.status == S.NeedsVerification:
            where = r.sign_in_ip
            if r.sign_in_country:
                where += f" / {r.sign_in_country}"
            print(f"\nWe emailed an 8-digit code to {r.masked_email} (from {where})")
            code = input("Enter the code: ").strip()
            authed = atlas.Account.SubmitVerification(code)

    elif choice == "3":
        # ================================================================
        # REGISTER - create the account and confirm the email if supplied.
        # Register does NOT sign you in - run this example again and pick
        # [2] to sign in whenever you're ready.
        # ================================================================
        username = input("Pick a username: ").strip()
        password = input("Pick a password: ").strip()
        email    = input("Email (optional - enter to skip): ").strip()

        if not atlas.Account.Register(username, password, email):
            print(f"\n[!] {atlas.Data.GetErrorMessage()}")
            input("\nPress Enter to exit...")
            return 1
        if atlas.Account.HasPendingEmailConfirm():
            print(f"\nWe emailed an 8-digit confirmation code to {email}.")
            code = input("Enter the code: ").strip()
            if not atlas.Account.ConfirmEmail(code):
                print(f"\n[!] {atlas.Data.GetErrorMessage()}")
                input("\nPress Enter to exit...")
                return 1
        print(f"\n[+] Account '{username}' is ready. "
              f"Run this example again and pick [2] to sign in.")
        input("\nPress Enter to exit...")
        return 0

    else:
        print("\nUnknown choice - exiting.")
        return 1

    if not authed:
        print(f"\n[!] Authentication failed. {atlas.Data.GetErrorMessage()}")
        input("\nPress Enter to exit...")
        return 1

    # On account sessions GetLicense() returns a synthetic "user:<name>" -
    # hide it and print Username instead. On license-only sessions Username
    # is empty and License is the real key.
    print("\n--- User Information ---")
    is_account = bool(atlas.Data.GetUsername())
    if is_account:
        print(f"Username:     {atlas.Data.GetUsername()}")
    else:
        print(f"License:      {atlas.Data.GetLicense()}")
    print(f"Expiry:       {atlas.Data.GetExpiry()}")
    print(f"IP:           {atlas.Data.GetIP()}")
    print(f"HWID:         {atlas.Data.GetHWID()}")
    print(f"Level:        {atlas.Data.GetLevel()}")
    print(f"Note:         {atlas.Data.GetNote()}")
    print(f"Active Users: {atlas.Data.GetActiveUserCount()}")
    print(f"Total Users:  {atlas.Data.GetUserCount()}")

    # Send a custom log message - appears in your dashboard Logs tab.
    atlas.Network.SubmitLog("User successfully completed the example")

    # ChangePassword is only meaningful on a password-mode session.
    if atlas.Data.GetUsername():
        yn = input("\nChange password? [y/N]: ").strip().lower()
        if yn == "y":
            oldp = input("Current password: ").strip()
            newp = input("New password: ").strip()
            if atlas.Network.ChangePassword(oldp, newp):
                print("[+] Password changed. Use the new password on your next sign-in.")
            else:
                print(f"[!] {atlas.Data.GetErrorMessage()}")

    # ================================================================
    # OPTIONAL - password reset flow. Not run inline (would interrupt
    # the session we just opened). Two calls, ready to lift:
    #
    #     atlas.Account.RequestPasswordReset("username-or-email")
    #     # ... user reads the 8-digit code from their email ...
    #     atlas.Account.CompletePasswordReset(code, new_password)
    # ================================================================

    input("\nPress Enter to exit program fully...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
