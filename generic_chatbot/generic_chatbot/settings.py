import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
ROOT_DIR = BASE_DIR.parent
dotenv_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path)


STATIC_ROOT = BASE_DIR / "staticfiles"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "!g8ik7!xk!9xyldg+r75$^@tdt+d")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = ["*"]

if DEBUG:
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

if not DEBUG:
    REDIS_URL = os.getenv(
        "REDIS_URL",
        "rediss://humanlikebotcache-5rqgxm.serverless.use1.cache.amazonaws.com:6379",
    )

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    },
}

# Append Elastic Beanstalk Load Balancer Health Check requests since the source host IP address keeps changing
if not DEBUG:
    try:
        token = requests.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        ).text
        internal_ip = requests.get(
            "http://169.254.169.254/latest/meta-data/local-ipv4",
            headers={"X-aws-ec2-metadata-token": token},
        ).text
    except requests.exceptions.ConnectionError:
        pass
    else:
        ALLOWED_HOSTS.append(internal_ip)
    del requests

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_redis",
    "chatbot",
    "rest_framework",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "https://dev.bot.wwbp.org",
    "https://bot.wwbp.org",
]

ROOT_URLCONF = "generic_chatbot.urls"


ASGI_APPLICATION = "generic_chatbot.asgi.application"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODERATION_VALUES_FOR_BLOCKED = json.loads(
    os.environ.get(
        "MODERATION_VALUES_FOR_BLOCKED",
        """{
            "harassment": 0.5,
            "harassment/threatening": 0.1,
            "hate": 0.5,
            "hate/threatening": 0.1,
            "self-harm": 0.2,
            "self-harm/instructions": 0.5,
            "self-harm/intent": 0.7,
            "sexual": 0.5,
            "sexual/minors": 0.2,
            "violence": 0.7,
            "violence/graphic": 0.8
        }""",
    ),
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR, "templates"],
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

WSGI_APPLICATION = "generic_chatbot.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USER"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("DATABASE_HOST"),
        "PORT": os.getenv("DATABASE_PORT"),
    },
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Add STATICFILES_DIRS for development
if DEBUG:
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]

# WhiteNoise configuration for both development and production
# This ensures consistent static file serving
STATICFILES_STORAGE = "whitenoise.storage.StaticFilesStorage"

# WhiteNoise configuration
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG  # Auto-refresh in development
WHITENOISE_MAX_AGE = (
    31536000 if not DEBUG else 0
)  # 1 year in production, no cache in dev
WHITENOISE_INDEX_FILE = True

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

X_FRAME_OPTIONS = "ALLOWALL"
# consider restricting in production
CORS_ALLOW_ALL_ORIGINS = True
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SECURE = True

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_TEMP_DIR = None
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Environment settings
BACKEND_ENVIRONMENT = os.getenv("BACKEND_ENVIRONMENT", "production")

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "detailed": {
            "format": "[{levelname}] {asctime} {name} {funcName}:{lineno} - {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "level": "DEBUG" if DEBUG else "INFO",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "detailed",
            "level": "INFO",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "error.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "detailed",
            "level": "ERROR",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "chatbot": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "chatbot.views": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "chatbot.services": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "chatbot.admin": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        "server": {
            "handlers": ["console", "file", "error_file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file", "error_file"],
        "level": "INFO",
    },
}
