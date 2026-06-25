"""
Configuration Django du projet Smart Campus (backend P3).

Toute la configuration sensible est lue depuis l'environnement (fichier `.env`
en développement, vraies variables d'environnement en production) via
`django-environ`. Aucun secret n'est écrit en dur ici.
"""
from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Chemins de base
# ---------------------------------------------------------------------------
# settings.py est dans core/, donc la racine du projet est le parent de core/.
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Lecture de l'environnement
# ---------------------------------------------------------------------------
env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    JWT_ALGORITHM=(str, "HS256"),
    MQTT_PORT=(int, 1883),
)

# Charge un fichier .env à la racine s'il existe (sans écraser l'env réel).
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Sécurité de base
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret-key-a-changer")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Applications installées
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # blacklist du refresh au logout
    "corsheaders",
    "drf_spectacular",  # génération de la documentation OpenAPI
]

LOCAL_APPS = [
    "core",        # base abstraite, crypto, commande seed_data
    "comptes",     # utilisateurs + rôles + auth JWT
    "etudiants",   # étudiants + cartes + certificats
    "terminaux",   # terminaux physiques
    "monetique",   # soldes + transactions
    "scolarite",   # paiements de scolarité + statut
    "iot",         # réception des scans (MQTT / HTTP)
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # doit être placé très haut
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------
# Par défaut : SQLite (développement/tests sans PostgreSQL). En production et
# via docker-compose, on fournit DATABASE_URL pointant vers PostgreSQL.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# ---------------------------------------------------------------------------
# Cache / Redis (optionnel ; tombe en LocMem si Redis indisponible)
# ---------------------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ---------------------------------------------------------------------------
# Modèle utilisateur personnalisé (4 rôles)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "comptes.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques / médias
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # Par défaut tout endpoint exige une authentification ; on ouvre
    # explicitement les routes publiques (login/refresh).
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.PaginationStandard",
    "PAGE_SIZE": 20,
    # Classe de schéma OpenAPI (drf-spectacular).
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        # Interface navigable seulement en debug (confort de développement).
        *(("rest_framework.renderers.BrowsableAPIRenderer",) if DEBUG else ()),
    ),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "auth": "10/min",   # protège le login contre le bruteforce
        "scan": "120/min",  # cadence raisonnable pour les terminaux
    },
}

# ---------------------------------------------------------------------------
# Documentation OpenAPI (drf-spectacular)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Smart Campus — API backend (P3)",
    "DESCRIPTION": (
        "API REST du système universitaire Smart Campus (ESP/UCAD).\n\n"
        "**Authentification** : JWT (Bearer). Récupérer un token via "
        "`POST /api/auth/login/`, puis l'envoyer dans l'en-tête "
        "`Authorization: Bearer <access>`.\n\n"
        "**Montants** : entiers en centimes de FCFA (750 FCFA = 75000).\n\n"
        "**Scans signés** : les endpoints de débit et `/api/iot/scan/` exigent "
        "une enveloppe signée par la carte (nonce + signature RSA). En dev, la "
        "générer avec `python manage.py simuler_scan`."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,  # n'expose pas le schéma brut dans Swagger
    "COMPONENT_SPLIT_REQUEST": True,  # sépare schémas de requête / réponse
    "SORT_OPERATIONS": False,
    # Regroupement logique des endpoints dans Swagger/ReDoc.
    "TAGS": [
        {"name": "Authentification", "description": "Connexion JWT et profil."},
        {"name": "Monétique", "description": "Soldes, débits, crédits, stats."},
        {"name": "Scolarité", "description": "Paiements, statut, reçus."},
        {"name": "IoT", "description": "Réception des scans de carte."},
        {"name": "Étudiants", "description": "Gestion des fiches étudiants."},
        {"name": "Terminaux", "description": "Gestion des terminaux."},
    ],
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,  # garde le token entre les rechargements
        "displayRequestDuration": True,
    },
    # Noms explicites pour les énumérations (plusieurs champs `statut`/`type`
    # partagent un nom et entreraient en collision sans ces alias).
    "ENUM_NAME_OVERRIDES": {
        "StatutCarteEnum": "etudiants.models.StatutCarte",
        "StatutTransactionEnum": "monetique.models.StatutTransaction",
        "StatutPaiementEnum": "scolarite.models.StatutPaiement",
        "TypeTransactionEnum": "monetique.models.TypeTransaction",
        "TypePeriodeEnum": "scolarite.models.TypePeriode",
        "TypeTerminalEnum": "terminaux.models.TypeTerminal",
        "TypeScanEnum": "iot.models.TypeScan",
        "RoleEnum": "comptes.models.Role",
    },
}

# ---------------------------------------------------------------------------
# Authentification JWT (djangorestframework-simplejwt)
# ---------------------------------------------------------------------------
# Algorithme : HS256 par défaut (simple, clé symétrique = SECRET_KEY) ; RS256
# recommandé en production (clé asymétrique). Décision signalée : on garde
# HS256 par défaut pour que le projet démarre sans génération de clés, mais
# RS256 est entièrement câblé ci-dessous si JWT_ALGORITHM=RS256.
JWT_ALGORITHM = env("JWT_ALGORITHM")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": JWT_ALGORITHM,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

if JWT_ALGORITHM == "RS256":
    # En RS256 : clé privée pour signer, clé publique pour vérifier.
    signing_path = env("JWT_SIGNING_KEY_PATH", default="")
    verifying_path = env("JWT_VERIFYING_KEY_PATH", default="")
    if signing_path and verifying_path:
        SIMPLE_JWT["SIGNING_KEY"] = Path(signing_path).read_text()
        SIMPLE_JWT["VERIFYING_KEY"] = Path(verifying_path).read_text()
else:
    # HS256 : la clé symétrique est SECRET_KEY (valeur par défaut de simplejwt).
    SIMPLE_JWT["SIGNING_KEY"] = SECRET_KEY

# ---------------------------------------------------------------------------
# CORS (le frontend est servi par une origine distincte)
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Chiffrement applicatif des données personnelles (AES-256-GCM)
# ---------------------------------------------------------------------------
# Clé en base64 (32 octets). Si absente, core.crypto la dérive de SECRET_KEY
# en émettant un avertissement (acceptable en dev uniquement).
CHAMP_CHIFFREMENT_CLE = env("CHAMP_CHIFFREMENT_CLE", default="")

# ---------------------------------------------------------------------------
# MQTT (réception des scans de carte simulés)
# ---------------------------------------------------------------------------
MQTT_HOST = env("MQTT_HOST", default="localhost")
MQTT_PORT = env("MQTT_PORT")
MQTT_TOPIC_SCAN = env("MQTT_TOPIC_SCAN", default="campus/reader/scan")
MQTT_USERNAME = env("MQTT_USERNAME", default="")
MQTT_PASSWORD = env("MQTT_PASSWORD", default="")

# Fenêtre d'acceptation d'un scan (anti-rejeu temporel) en secondes.
SCAN_TTL_SECONDES = env.int("SCAN_TTL_SECONDES", default=30)

# ---------------------------------------------------------------------------
# Établissement (affiché sur les reçus PDF)
# ---------------------------------------------------------------------------
ETABLISSEMENT_NOM = env(
    "ETABLISSEMENT_NOM", default="École Supérieure Polytechnique — UCAD"
)
ETABLISSEMENT_VILLE = env("ETABLISSEMENT_VILLE", default="Dakar, Sénégal")

# ---------------------------------------------------------------------------
# Journalisation
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # Logger métier dédié à la sécurité (scans refusés, replay, signatures).
        "smartcampus.securite": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
