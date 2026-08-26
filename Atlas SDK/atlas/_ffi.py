"""ctypes bindings for Atlas.dll. One line per Atlas_* export. No logic here.

Public API lives in atlas/__init__.py - this module is an implementation detail.
"""
import os, sys, tempfile, atexit
from ctypes import CDLL, POINTER, c_char_p, c_int, c_size_t, c_uint8, create_string_buffer
from pathlib import Path


def _dll_path():
    # 1. Explicit override wins.
    env = os.environ.get("ATLAS_DLL_PATH")
    if env:
        return env

    # 2. Frozen (PyInstaller): look next to the exe, then in sys._MEIPASS.
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "Atlas.dll")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "Atlas.dll")

    # 3. Source checkout: package sits next to Atlas.dll in the SDK tree.
    candidates.append(Path(__file__).resolve().parent.parent / "Atlas.dll")

    for p in candidates:
        try:
            if p.is_file():
                return str(p)
        except OSError:
            pass

    # 4. PyInstaller archive fallback: read the bundled bytes, stage to %TEMP%.
    pkg_dir = Path(__file__).resolve().parent.parent
    bundled_path = pkg_dir / "Atlas.dll"
    try:
        data = bundled_path.read_bytes()
    except OSError:
        raise FileNotFoundError(
            "Atlas.dll not found. Run from SDK tree, frozen via PyInstaller, "
            "or set ATLAS_DLL_PATH."
        )

    out_dir = Path(tempfile.gettempdir()) / "atlas-sdk"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"Atlas-{os.getpid()}.dll"
    out_path.write_bytes(data)
    try:
        os.chmod(out_path, 0o600)
    except OSError:
        pass
    atexit.register(lambda p=out_path: _cleanup(p))
    return str(out_path)


def _cleanup(p):
    try:
        p.unlink()
    except OSError:
        pass


lib = CDLL(_dll_path())


def _sig(name, restype, *argtypes):
    fn = getattr(lib, name)
    fn.restype = restype
    fn.argtypes = list(argtypes)
    return fn


# One line per Atlas_* export. Names mirror Atlas.dll verbatim.

# -- lifecycle --
SetApiKey             = _sig("Atlas_SetApiKey",             c_int,  c_char_p)
Startup               = _sig("Atlas_Startup",               c_int)
Logout                = _sig("Atlas_Logout",                c_int)
Exit                  = _sig("Atlas_Exit",                  None)

# -- license --
Login                 = _sig("Atlas_Login",                 c_int,  c_char_p)
LoginUser             = _sig("Atlas_LoginUser",             c_int,  c_char_p, c_char_p)
Register              = _sig("Atlas_Register",              c_int,  c_char_p, c_char_p, c_char_p)

# -- account --
LoginAccountEx        = _sig("Atlas_LoginAccountEx",        c_int,  c_char_p, c_char_p, POINTER(c_int))
SubmitVerify          = _sig("Atlas_SubmitVerify",          c_int,  c_char_p)
ResendVerify          = _sig("Atlas_ResendVerify",          c_int)
RegisterAccount       = _sig("Atlas_RegisterAccount",       c_int,  c_char_p, c_char_p, c_char_p)
ConfirmEmail          = _sig("Atlas_ConfirmEmail",          c_int,  c_char_p)
HasPendingEmailConfirm= _sig("Atlas_HasPendingEmailConfirm",c_int)
RedeemKey             = _sig("Atlas_RedeemKey",             c_int,  c_int,    c_char_p)
RequestPasswordReset  = _sig("Atlas_RequestPasswordReset",  c_int,  c_char_p)
CompletePasswordReset = _sig("Atlas_CompletePasswordReset", c_int,  c_char_p, c_char_p)
ChangePassword        = _sig("Atlas_ChangePassword",        c_int,  c_char_p, c_char_p)

# -- last-verify context (set by LoginAccountEx on NEEDS_VERIFY) --
GetLastVerifyMaskedEmail = _sig("Atlas_GetLastVerifyMaskedEmail", c_int, c_char_p, c_size_t)
GetLastVerifyIP          = _sig("Atlas_GetLastVerifyIP",          c_int, c_char_p, c_size_t)
GetLastVerifyCountry     = _sig("Atlas_GetLastVerifyCountry",     c_int, c_char_p, c_size_t)

# -- network --
CheckAuthentication   = _sig("Atlas_CheckAuthentication",   c_int)
Ping                  = _sig("Atlas_Ping",                  c_int)
BanUser               = _sig("Atlas_BanUser",               c_int,  c_char_p, c_int)
SubmitLog             = _sig("Atlas_SubmitLog",             c_int,  c_char_p)
Download              = _sig("Atlas_Download",              c_int,  c_int, POINTER(c_uint8), c_size_t)

# -- data (size-query pattern: (NULL, 0) -> bytes needed, then alloc + retry) --
GetLicense            = _sig("Atlas_GetLicense",            c_int,  c_char_p, c_size_t)
GetUsername           = _sig("Atlas_GetUsername",           c_int,  c_char_p, c_size_t)
GetEmail              = _sig("Atlas_GetEmail",              c_int,  c_char_p, c_size_t)
GetPassword           = _sig("Atlas_GetPassword",           c_int,  c_char_p, c_size_t)
GetHWID               = _sig("Atlas_GetHWID",               c_int,  c_char_p, c_size_t)
GetIP                 = _sig("Atlas_GetIP",                 c_int,  c_char_p, c_size_t)
GetExpiry             = _sig("Atlas_GetExpiry",             c_int,  c_char_p, c_size_t)
GetNote               = _sig("Atlas_GetNote",               c_int,  c_char_p, c_size_t)
GetDevice             = _sig("Atlas_GetDevice",             c_int,  c_char_p, c_size_t)
GetFirstSeenDate      = _sig("Atlas_GetFirstSeenDate",      c_int,  c_char_p, c_size_t)
GetLastSeenDate       = _sig("Atlas_GetLastSeenDate",       c_int,  c_char_p, c_size_t)
GetUserCount          = _sig("Atlas_GetUserCount",          c_int,  c_char_p, c_size_t)
GetActiveUserCount    = _sig("Atlas_GetActiveUserCount",    c_int,  c_char_p, c_size_t)
GetErrorMessage       = _sig("Atlas_GetErrorMessage",       c_int,  c_char_p, c_size_t)
GetLevel              = _sig("Atlas_GetLevel",              c_int)
GetUserId             = _sig("Atlas_GetUserId",             c_int)
GetDaysRemaining      = _sig("Atlas_GetDaysRemaining",      c_int)
IsLifetime            = _sig("Atlas_IsLifetime",            c_int)
IsExpiringSoon        = _sig("Atlas_IsExpiringSoon",        c_int,  c_int)
IsAuthenticated       = _sig("Atlas_IsAuthenticated",       c_int)
IsBanned              = _sig("Atlas_IsBanned",              c_int)
HasError              = _sig("Atlas_HasError",              c_int)
ClearError            = _sig("Atlas_ClearError",            None)

# -- variables --
VariableFetch         = _sig("Atlas_VariableFetch",         c_int,  c_char_p, c_char_p, c_size_t)
VariableFetchBool     = _sig("Atlas_VariableFetchBool",     c_int,  c_char_p)
VariableFetchInt      = _sig("Atlas_VariableFetchInt",      c_int,  c_char_p)

# -- webhook --
WebhookSendDiscord      = _sig("Atlas_WebhookSendDiscord",      c_int, c_char_p, c_char_p)
WebhookSendDiscordEmbed = _sig("Atlas_WebhookSendDiscordEmbed", c_int, c_char_p, c_char_p, c_char_p, c_int)
WebhookSend             = _sig("Atlas_WebhookSend",             c_int, c_char_p, c_char_p)


def read_str(fn, *args) -> str:
    """Two-call size-query for Atlas_* string getters."""
    n = fn(*args, None, 0) if args else fn(None, 0)
    if n <= 0:
        return ""
    buf = create_string_buffer(n)
    fn(*args, buf, n) if args else fn(buf, n)
    return buf.raw[:max(0, n - 1)].decode("utf-8", errors="replace")


def read_bytes(file_id: int) -> bytes:
    """Two-call size-query for Atlas_Download. Returns b'' on failure / not found."""
    n = Download(file_id, None, 0)
    if n <= 0:
        return b""
    buf = (c_uint8 * n)()
    rc = Download(file_id, buf, n)
    if rc <= 0:
        return b""
    return bytes(buf[:rc])
