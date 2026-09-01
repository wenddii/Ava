from pathlib import Path
import os
import sys

import dj_database_url
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / "config" / ".env")

import cloudinary
import cloudinary.uploader


# ------------------------------------------------------------------------------
# Base Directory
# ------------------------------------------------------------------------------



# ------------------------------------------------------------------------------
# Security
# ------------------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-local-key"
)

DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS =  ['*']



# ------------------------------------------------------------------------------
# Installed Apps
# ------------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "cloudinary",
    "cloudinary_storage",

    "website",
    "dashboard",

    "telegram_bot",
]


# ------------------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


# ------------------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates"
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# ------------------------------------------------------------------------------
# Database
# ------------------------------------------------------------------------------

db_url = os.getenv("DATABASE_URL")

if "test" in sys.argv or not db_url:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": dj_database_url.config(
            default=db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }


# ------------------------------------------------------------------------------
# Password Validation
# ------------------------------------------------------------------------------

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


# ------------------------------------------------------------------------------
# Internationalization
# ------------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Africa/Addis_Ababa"

USE_I18N = True

USE_TZ = True


# ------------------------------------------------------------------------------
# Static Files
# ------------------------------------------------------------------------------

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ------------------------------------------------------------------------------
# Media Files
# ------------------------------------------------------------------------------

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ------------------------------------------------------------------------------
# Cloudinary / Storage Configuration
# ------------------------------------------------------------------------------

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")


if "test" in sys.argv or not (
    CLOUDINARY_CLOUD_NAME
    and CLOUDINARY_API_KEY
    and CLOUDINARY_API_SECRET
):
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }

else:
    STORAGES = {
        "default": {
            "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
    )


# ------------------------------------------------------------------------------
# Login URL Settings
# ------------------------------------------------------------------------------

LOGIN_URL = "dashboard_login"

LOGIN_REDIRECT_URL = "dashboard_index"


# ------------------------------------------------------------------------------
# Default Primary Key
# ------------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")