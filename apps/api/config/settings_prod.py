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
    raise RuntimeError(
        "SECRET_KEY é obrigatória em produção."
    )


# ============================================================
# HOSTS
# ============================================================

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        ".onrender.com"
    ).split(",")
    if host.strip()
]


# ============================================================
# PROXY / HTTPS
# ============================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_SSL_REDIRECT = False  # Desativado para permitir acesso via HTTP em render.com


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
    # Desenvolvimento local - Frontend
    "http://localhost:8080",
    "http://127.0.0.1:8080",

    # Desenvolvimento local - Backend
    "http://localhost:8000",
    "http://127.0.0.1:8000",

    # Frontend Vercel
    "https://data-dojo-nine.vercel.app",
    "https://data-dojo-nar3.vercel.app",
]

# Permite adicionar origens através do .env
CUSTOM_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    ""
)

if CUSTOM_ORIGINS:
    CORS_ALLOWED_ORIGINS.extend(
        [
            origin.strip()
            for origin in CUSTOM_ORIGINS.split(",")
            if origin.strip()
        ]
    )

# Permite previews da Vercel
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.vercel\.app$",
]

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