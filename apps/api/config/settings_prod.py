from .settings import *


# ============================================================
# AMBIENTE
# ============================================================

ENVIRONMENT = "production"
DEBUG = False


# ============================================================
# SECRET KEY
# ============================================================

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY é obrigatória em produção.")


# ============================================================
# HOSTS
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", ".onrender.com").split(",")
    if host.strip()
]


# ============================================================
# PROXY / HTTPS
# ============================================================

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False


# ============================================================
# COOKIES
# ============================================================

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "None"

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "None"


# ============================================================
# HSTS
# ============================================================

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False


# ============================================================
# CORS
# ============================================================

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "https://data-dojo-nine.vercel.app",
    "https://data-dojo-nar3.vercel.app",
]

CUSTOM_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "")
if CUSTOM_ORIGINS:
    CORS_ALLOWED_ORIGINS.extend(
        origin.strip()
        for origin in CUSTOM_ORIGINS.split(",")
        if origin.strip()
    )

CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://.*\.vercel\.app$"]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]


# ============================================================
# CSRF
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

# Mantém as origens HTTPS do frontend explicitamente confiáveis.
for origin in CORS_ALLOWED_ORIGINS:
    if origin.startswith("https://") and origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(origin)


# ============================================================
# SEGURANÇA ADICIONAL
# ============================================================

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].update({
    "ai_anon": os.getenv("AI_ANON_THROTTLE_RATE", "20/hour"),
    "ai_user": os.getenv("AI_USER_THROTTLE_RATE", "100/hour"),
})
