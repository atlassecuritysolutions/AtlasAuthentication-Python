/*
 * Atlas.c.h — plain C header for the Atlas.dll ABI. Windows x64 only.
 *
 * This describes the extern "C" DLL surface produced by AtlasExports.cpp.
 * Not to be confused with the C++ header (Atlas.h) — that one exposes the
 * namespaced C++ API for static-library consumers. Non-C++ bindings
 * (Python ctypes, Rust bindgen, Zig, cffi) can't parse the C++ header;
 * this is the one they can.
 *
 * Every extern here maps 1:1 to a __declspec(dllexport) in AtlasExports.cpp.
 * All calls are __cdecl. Status codes are stable and add-only.
 *
 * Header targets DLL surface v1.0.0. Call Atlas_Version() at runtime to
 * read the loaded DLL's actual version.
 */

#ifndef ATLAS_C_H
#define ATLAS_C_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* -- status codes ---------------------------------------------------------- */
/* Stable numeric contract - do not renumber. Add-only. */
#define ATLAS_OK                    0
#define ATLAS_ERR_NOT_STARTED       1
#define ATLAS_ERR_NO_API_KEY        2
#define ATLAS_ERR_LOGIN_FAILED      3
#define ATLAS_ERR_NOT_AUTHED        4
#define ATLAS_ERR_BAD_ARG           5
#define ATLAS_ERR_BUFFER_TOO_SMALL  6
#define ATLAS_ERR_SERVER            7
#define ATLAS_ERR_INTERNAL          8
/* Account-mode: server wants an 8-digit verification code from the user.
 * The SDK is holding the challenge until Atlas_SubmitVerify() is called. */
#define ATLAS_ERR_NEEDS_VERIFY      10

/* -- DLL calling convention ------------------------------------------------ */
#if defined(_WIN32) || defined(_WIN64)
    #define ATLAS_CALL __cdecl
    #if defined(ATLAS_STATIC)
        #define ATLAS_API
    #elif defined(ATLAS_BUILD_DLL)
        #define ATLAS_API __declspec(dllexport)
    #else
        #define ATLAS_API __declspec(dllimport)
    #endif
#else
    #define ATLAS_CALL
    #define ATLAS_API
#endif

/* -- lifecycle ------------------------------------------------------------- */

/* Set the API key. Must be called BEFORE Atlas_Startup().
 * Returns: ATLAS_OK, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_SetApiKey(const char* api_key);

/* -- apphash overrides ----------------------------------------------------
 * The DLL's default apphash is SHA-256 of GetModuleFileNameA(NULL) - under
 * a non-C++ host that's node.exe / dotnet.exe / python.exe, NOT the file
 * that identifies the developer's application. These overrides let a
 * binding pin the apphash to something meaningful.
 *
 * Both are one-shot per process AND lock after Atlas_Startup(). Post-init
 * writes return ATLAS_ERR_BAD_ARG. See AppHash.md for the threat model.
 */

/* Override the file whose SHA-256 becomes the apphash. Path validated
 * (non-empty, <=32767 chars); file is read at server-call time.
 * Returns: ATLAS_OK, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_SetAppHashPath(const char* path);

/* Set the apphash directly. Input MUST be lowercase-hex SHA-256:
 * exactly 64 chars, [0-9a-f] only. Empty / uppercase / any other input
 * rejected - no way to nullify the hash and bypass server whitelisting.
 * Returns: ATLAS_OK, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_SetAppHash(const char* hex64);

/* Read the apphash that WILL be sent to the server on the next request.
 * Callable pre or post Startup. Size-query pattern. Empty string if the
 * source file couldn't be read. */
ATLAS_API int ATLAS_CALL Atlas_GetResolvedAppHash(char* out, size_t out_size);

/* Optional: set headless mode. When quiet=1, startup failures return
 * ATLAS_ERR_INTERNAL instead of showing a modal MessageBox. Bindings for
 * headless hosts (Node service, .NET daemon) should call this with quiet=1
 * before Atlas_Startup(). Default is 0 (modal on failure).
 *
 * NOTE: server-driven MessageBoxes (dashboard "send message", MSG| frames
 * on heartbeat, startup/login banners) are NOT affected by SetQuiet - those
 * always render. SetQuiet only silences the DLL's own client-side failure
 * modals so a headless daemon can surface errors through its own channels.
 * Returns: ATLAS_OK. */
ATLAS_API int ATLAS_CALL Atlas_SetQuiet(int quiet);

/* Initialize the Atlas protection stack. Idempotent - safe to call more
 * than once but only takes effect on the first successful call.
 * Returns: ATLAS_OK, ATLAS_ERR_NO_API_KEY, ATLAS_ERR_INTERNAL. */
ATLAS_API int ATLAS_CALL Atlas_Startup(void);

/* -- license-mode auth ----------------------------------------------------- */

/* Authenticate a license key. Returns ATLAS_OK on success. On server
 * rejection returns ATLAS_ERR_LOGIN_FAILED - call Atlas_GetErrorMessage()
 * for the reason. Any other return is a transport or precondition failure.
 * Returns: ATLAS_OK, ATLAS_ERR_LOGIN_FAILED, ATLAS_ERR_NOT_STARTED,
 *          ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_Login(const char* license);

/* Legacy per-license username+password. New code should prefer the
 * account-mode helpers below (Atlas_LoginAccountEx). Kept for parity with
 * the C++ Atlas::Login(user, pass) overload.
 * Returns: ATLAS_OK, ATLAS_ERR_LOGIN_FAILED, ATLAS_ERR_NOT_STARTED,
 *          ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_LoginUser(const char* username, const char* password);

/* One-shot: bind a license key to a new username+password on the same
 * key row. Does NOT sign the caller in - a follow-up Atlas_LoginUser is
 * required to open a session.
 * Returns: ATLAS_OK, ATLAS_ERR_LOGIN_FAILED, ATLAS_ERR_NOT_STARTED,
 *          ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_Register(const char* license,
                                        const char* username,
                                        const char* password);

/* -- account-mode auth (Atlas 2.0 accounts) ------------------------------- */

/* Sign in with account username+password. On success returns ATLAS_OK and
 * writes the account's user_id to *out_user_id. If the server requires
 * email verification (new device, policy trigger), returns
 * ATLAS_ERR_NEEDS_VERIFY - the SDK is holding the challenge until
 * Atlas_SubmitVerify() is called with the 8-digit code the server emailed.
 * Returns: ATLAS_OK, ATLAS_ERR_NEEDS_VERIFY, ATLAS_ERR_LOGIN_FAILED,
 *          ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_LoginAccountEx(const char* username,
                                              const char* password,
                                              int* out_user_id);

/* Submit the 8-digit code the server emailed after a NEEDS_VERIFY reply.
 * On success the session is fully opened (same shape as ATLAS_OK from
 * Atlas_LoginAccountEx).
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_SubmitVerify(const char* eight_digit_code);

/* Ask the server to resend the verification code. Rate-limited by the
 * server (~60s between resends).
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED. */
ATLAS_API int ATLAS_CALL Atlas_ResendVerify(void);

/* Create a new account. Does NOT sign the caller in. Pass email=NULL or
 * email="" to register without an email (skips email-confirm).
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_RegisterAccount(const char* username,
                                               const char* password,
                                               const char* email);

/* Redeem a license key against the signed-in account. Adds days to the
 * account's expiry. Pass user_id=0 to use the id captured at login.
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_RedeemKey(int user_id, const char* license_key);

/* Request a password reset. Server always returns OK (anti-enumeration);
 * if the identifier resolved to a real user with an email, that user
 * receives an 8-digit code.
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_RequestPasswordReset(const char* identifier);

/* Complete a password reset with the 8-digit code + new password.
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_CompletePasswordReset(const char* eight_digit_code,
                                                     const char* new_password);

/* Change the signed-in account's password. Only valid after a successful
 * Atlas_LoginUser / Atlas_LoginAccountEx session.
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_ChangePassword(const char* old_password,
                                              const char* new_password);

/* Confirm a newly-registered account's email address with the 8-digit code
 * the server emailed. Distinct from Atlas_SubmitVerify (which consumes the
 * sign-in verify challenge); this one consumes the post-Register challenge.
 * Returns: ATLAS_OK, ATLAS_ERR_SERVER, ATLAS_ERR_NOT_STARTED, ATLAS_ERR_BAD_ARG. */
ATLAS_API int ATLAS_CALL Atlas_ConfirmEmail(const char* eight_digit_code);

/* 1 if the most recent Atlas_RegisterAccount returned a confirm-token that
 * hasn't been consumed yet, else 0. Bindings use this to decide whether to
 * prompt the user for the emailed code after a successful Register. */
ATLAS_API int ATLAS_CALL Atlas_HasPendingEmailConfirm(void);

/* -- last-verify context (size-query pattern) ------------------------------
 * Populated by Atlas_LoginAccountEx when it returns ATLAS_ERR_NEEDS_VERIFY.
 * All three empty when no verify is pending or the server didn't include the
 * field. Cleared when Atlas_SubmitVerify succeeds or terminally fails.
 *
 * masked_email:  "ob...d@gmail.com"
 * ip:            server-detected client IP
 * country:       2-letter ISO ("US", "SA", ...) */
ATLAS_API int ATLAS_CALL Atlas_GetLastVerifyMaskedEmail(char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetLastVerifyIP          (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetLastVerifyCountry     (char* out, size_t out_size);

/* -- session state --------------------------------------------------------- */

/* 1 if the current session is authenticated, else 0. */
ATLAS_API int ATLAS_CALL Atlas_IsAuthenticated(void);

/* 1 if the current account is banned, else 0. Not mutually exclusive with
 * Atlas_IsAuthenticated - a ban can arrive between heartbeats. */
ATLAS_API int ATLAS_CALL Atlas_IsBanned(void);

/* 1 if Atlas is loaded as a DLL (which it always is if you're reading this
 * header - the static-lib path uses Atlas.h, not Atlas.c.h). */
ATLAS_API int ATLAS_CALL Atlas_IsDllHost(void);

/* Terminate the host process through the SDK's own kill path. Prefer this
 * to a language-level exit - a soft exit can be patched out by an attacker
 * where this routes through the DLL's kernel-level fastfail. */
ATLAS_API void ATLAS_CALL Atlas_Exit(void);

/* Gentle sign-out. Tells the server to tear down the session and stops
 * the SDK's heartbeat thread. Contrast with Atlas_Exit which is the hard
 * "attacker detected" kill.
 * Returns: ATLAS_OK, ATLAS_ERR_NOT_STARTED. */
ATLAS_API int ATLAS_CALL Atlas_Logout(void);

/* -- network --------------------------------------------------------------- */

/* On-demand session revalidation. Returns ATLAS_OK if still valid,
 * ATLAS_ERR_SERVER if not. The DLL's own heartbeat runs regardless (5s
 * poll for account sessions, persistent socket for license sessions);
 * this is for explicit checkpoints before a sensitive action. */
ATLAS_API int ATLAS_CALL Atlas_CheckAuthentication(void);

/* Round-trip latency to the auth server in milliseconds. -1 if unreachable. */
ATLAS_API int ATLAS_CALL Atlas_Ping(void);

/* Ban the current user. duration_minutes=0 means permanent. Requires
 * appropriate dashboard permissions on the API key.
 * Returns: ATLAS_OK, ATLAS_ERR_NOT_AUTHED, ATLAS_ERR_SERVER,
 *          ATLAS_ERR_BAD_ARG, ATLAS_ERR_NOT_STARTED. */
ATLAS_API int ATLAS_CALL Atlas_BanUser(const char* reason, int duration_minutes);

/* Write a custom log entry visible on the dashboard Logs tab.
 * Returns: ATLAS_OK, ATLAS_ERR_NOT_AUTHED, ATLAS_ERR_SERVER,
 *          ATLAS_ERR_BAD_ARG, ATLAS_ERR_NOT_STARTED. */
ATLAS_API int ATLAS_CALL Atlas_SubmitLog(const char* log_text);

/* Fetch a panel-uploaded file by numeric ID.
 * Size-query pattern:
 *   1st call: out=NULL, out_size=0  -> returns bytes needed (positive)
 *   2nd call: out=alloc(N), out_size=N -> returns bytes written (positive)
 * Negative return: -status code (e.g. -ATLAS_ERR_SERVER = -7).
 * Zero return: file not found or empty. */
ATLAS_API int ATLAS_CALL Atlas_Download(int file_id, uint8_t* out, size_t out_size);

/* -- data accessors -------------------------------------------------------- */
/* For every string getter below (returns int, takes out/out_size):
 *   Pass out=NULL, out_size=0 -> returns bytes needed (including NUL).
 *   Pass out=alloc(N), out_size=N -> writes NUL-terminated string, returns
 *     bytes written (including NUL).
 *   Negative return: -ATLAS_ERR_BUFFER_TOO_SMALL if out_size < needed. */

ATLAS_API int ATLAS_CALL Atlas_GetLicense        (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetUsername       (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetEmail          (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetPassword       (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetHWID           (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetIP             (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetExpiry         (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetNote           (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetDevice         (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetFirstSeenDate  (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetLastSeenDate   (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetUserCount      (char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetActiveUserCount(char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_GetErrorMessage   (char* out, size_t out_size);

/* Numeric access level for the session. 0 when unknown / not signed in. */
ATLAS_API int ATLAS_CALL Atlas_GetLevel(void);

/* -- expiry helpers -------------------------------------------------------- */

/* Days remaining on the current session.
 *   -1 = lifetime (no expiry set)
 *    0 = expired
 *   >0 = days left */
ATLAS_API int ATLAS_CALL Atlas_GetDaysRemaining(void);

/* 1 if the session has no expiry (lifetime), else 0. */
ATLAS_API int ATLAS_CALL Atlas_IsLifetime(void);

/* 1 if the session expires within days_threshold days.
 * Pass days_threshold=0 to accept the SDK's default (7 days). */
ATLAS_API int ATLAS_CALL Atlas_IsExpiringSoon(int days_threshold);

/* -- error state ----------------------------------------------------------- */

/* 1 if Atlas_GetErrorMessage would return a non-empty string, else 0. */
ATLAS_API int ATLAS_CALL Atlas_HasError(void);

/* Reset the error state. Atlas_GetErrorMessage returns "" until the next
 * error is recorded. */
ATLAS_API void ATLAS_CALL Atlas_ClearError(void);

/* -- variables ------------------------------------------------------------- */
/* Dashboard-configured key/value pairs. Fetch returns "" for missing keys;
 * FetchBool / FetchInt return 0 for missing or unparseable values. */

ATLAS_API int ATLAS_CALL Atlas_VariableFetch    (const char* key, char* out, size_t out_size);
ATLAS_API int ATLAS_CALL Atlas_VariableFetchBool(const char* key);
ATLAS_API int ATLAS_CALL Atlas_VariableFetchInt (const char* key);

/* -- webhooks -------------------------------------------------------------- */
/* Fire-and-forget outbound HTTP POST. Unrelated to Atlas auth — exposed
 * for bindings that want to notify Discord/Slack/custom endpoints without
 * pulling a second HTTP dependency. Color is 0xRRGGBB (0x3498db default). */

ATLAS_API int ATLAS_CALL Atlas_WebhookSendDiscord     (const char* url, const char* message);
ATLAS_API int ATLAS_CALL Atlas_WebhookSendDiscordEmbed(const char* url, const char* title,
                                                       const char* description, int color);
ATLAS_API int ATLAS_CALL Atlas_WebhookSend            (const char* url, const char* json_payload);

/* Signed-in account's user_id. 0 = not signed in OR license-only session
 * (license mode has no user_id concept). */
ATLAS_API int ATLAS_CALL Atlas_GetUserId(void);

/* Seconds remaining on the current session.
 *   -1 = lifetime / unlimited (no expiry set)
 *    0 = expired
 *   >0 = seconds left
 * Returned as int64_t for FFI portability; callers that treat -1 as
 * "unlimited" get the correct semantic. */
ATLAS_API int64_t ATLAS_CALL Atlas_GetSecondsUntilExpiry(void);

/* -- metadata -------------------------------------------------------------- */

/* Semver of the DLL surface. Bindings pin against a minimum. */
ATLAS_API int ATLAS_CALL Atlas_Version(char* out, size_t out_size);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* ATLAS_C_H */
