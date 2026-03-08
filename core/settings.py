
# #########################################################################################################

# from pathlib import Path
# import os
# from django.contrib.messages import constants as messages
# import dj_database_url

# # Load environment variables
# def get_env_bool(name, default=False):
#     """Convert environment variable to boolean."""
#     value = os.getenv(name, str(default))
#     return value.lower() in ('true', '1', 'yes')

# def get_env_list(name, default=''):
#     """Convert comma-separated environment variable to list."""
#     value = os.getenv(name, default)
#     return [item.strip() for item in value.split(',') if item.strip()]

# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# # Build paths inside the project like this: BASE_DIR / 'subdir'.
# BASE_DIR = Path(__file__).resolve().parent.parent

# # Quick-start development settings - unsuitable for production
# # See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# # SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = os.getenv(
#     'SECRET_KEY',
#     'django-insecure-_q5%&jqm$884a0b!an#-we^fx&22(%u+rdp1#7g83on=6f&moa'  # Fallback for local dev
# )

# # SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = get_env_bool('DEBUG', True)

# # Parse ALLOWED_HOSTS from environment variable
# ALLOWED_HOSTS = get_env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')

# # Application definition

# INSTALLED_APPS = [
#     'rest_framework',  # required for django rest framework
#     'widget_tweaks',  # required dependency
#     'django.contrib.admin',
#     'django.contrib.auth',
#     'django.contrib.contenttypes',
#     'django.contrib.sessions',
#     'django.contrib.messages',
#     'django.contrib.humanize',
#     'django.contrib.staticfiles',
#     'core.apps.CoreConfig',  # To load predefined qualifications
#     'django_extensions',
# ]

# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'whitenoise.middleware.WhiteNoiseMiddleware',
#     'django.contrib.sessions.middleware.SessionMiddleware',
#     'django.middleware.common.CommonMiddleware',
#     'django.middleware.csrf.CsrfViewMiddleware',
#     'django.contrib.auth.middleware.AuthenticationMiddleware',
#     'django.contrib.messages.middleware.MessageMiddleware',
#     'django.middleware.clickjacking.XFrameOptionsMiddleware',
# ]

# ROOT_URLCONF = 'core.urls'

# TEMPLATES = [
#     {
#         'BACKEND': 'django.template.backends.django.DjangoTemplates',
#         'DIRS': [BASE_DIR / 'templates'],
#         'APP_DIRS': True,
#         'OPTIONS': {
#             'context_processors': [
#                 'django.template.context_processors.request',
#                 'django.contrib.auth.context_processors.auth',
#                 'django.contrib.messages.context_processors.messages',
#                 'core.context_processors.notifications_context',
#             ],
#         },
#     },
# ]

# WSGI_APPLICATION = 'core.wsgi.application'

# # Database
# # https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# # Use dj-database-url to parse DATABASE_URL environment variable
# # Falls back to SQLite3 for local development
# DATABASE_URL = os.getenv('DATABASE_URL', None)

# if DATABASE_URL:
#     # Production: Use PostgreSQL via DATABASE_URL
#     DATABASES = {
#         'default': dj_database_url.config(
#             default=DATABASE_URL,
#             conn_max_age=600,
#             conn_health_checks=True,
#         )
#     }
# else:
#     # Development: Use SQLite
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }


# # Media files (User uploads)
# MEDIA_URL = os.getenv('MEDIA_URL', '/media/')
# MEDIA_ROOT = os.getenv('MEDIA_ROOT', os.path.join(BASE_DIR, 'media'))

# # Create media directory if it doesn't exist
# os.makedirs(MEDIA_ROOT, exist_ok=True)

# # Static files (CSS, JavaScript, Images)
# # https://docs.djangoproject.com/en/5.2/howto/static-files/
# STATIC_URL = os.getenv('STATIC_URL', 'static/')
# STATIC_ROOT = os.getenv('STATIC_ROOT', os.path.join(BASE_DIR, 'staticfiles'))

# # WhiteNoise configuration for static file serving in production
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# # Password validation
# AUTH_PASSWORD_VALIDATORS = [
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#     },
# ]

# AUTH_USER_MODEL = 'core.CustomUser'

# AUTHENTICATION_BACKENDS = [
#     'core.authback.EmailBackend',
#     'django.contrib.auth.backends.ModelBackend',
# ]

# # Email configuration
# # https://docs.djangoproject.com/en/5.2/topics/email/
# EMAIL_BACKEND = os.getenv(
#     'EMAIL_BACKEND',
#     'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
# )

# if not DEBUG:
#     # Production email settings
#     EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
#     EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
#     EMAIL_USE_TLS = get_env_bool('EMAIL_USE_TLS', True)
#     EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
#     EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
#     DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@lms.com')

# MESSAGE_TAGS = {
#     messages.DEBUG: 'secondary',
#     messages.INFO: 'info',
#     messages.SUCCESS: 'success',
#     messages.WARNING: 'warning',
#     messages.ERROR: 'danger',
# }

# # Internationalization
# LANGUAGE_CODE = 'en-us'
# TIME_ZONE = 'UTC'
# USE_I18N = True
# USE_TZ = True

# # Default primary key field type
# DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# #P36
# #p36


from pathlib import Path
import os
from django.contrib.messages import constants as messages
import dj_database_url

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-_q5%&jqm$884a0b!an#-we^fx&22(%u+rdp1#7g83on=6f&moa'

# 🚨 TEMPORARY DEMO CHANGE - Set DEBUG to True
DEBUG = True  # Changed from False to True

# 🚨 TEMPORARY DEMO CHANGE - Allow all hosts for demo
ALLOWED_HOSTS = ['*']  # Changed from specific hosts to allow all

# Application definition

INSTALLED_APPS = [
    'rest_framework',  # required for django rest framework
    'widget_tweaks',  # required dependency
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',  # To load predefined qualifications
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.notifications_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database


# DATABASES = {
#     'default': {
#          'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#    }
#  }
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'chietalms2_db',
#         'USER': 'chietalms2_db_user',
#         'PASSWORD': 'mFKMbEqiFi71BaKwKJYOJmhUrweuqaF6',
#         'HOST': 'dpg-d5nkdv4mrvns73fq08bg-a.oregon-postgres.render.com',
#         'PORT': '5432',
#     }
# }

DATABASES = {
   'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'test_chieta',           
        'USER': 'postgres',
        'PASSWORD': '12345',  
        'HOST': 'localhost',
        'PORT': '5432',
    }
}


MEDIA_URL = '/media/'
MEDIA_ROOT = '/var/data/media'

# 🚨 TEMPORARY DEMO CHANGE - Create media folder on startup
os.makedirs(MEDIA_ROOT, exist_ok=True)

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'core.CustomUser'

AUTHENTICATION_BACKENDS = [
    'core.authback.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Email configuration 
# 🚨 TEMPORARY DEMO CHANGE - Real email sending for demo
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'stemappza@gmail.com'
EMAIL_HOST_PASSWORD = 'ddtz gltz vscj loab'  # Your app password
DEFAULT_FROM_EMAIL = 'STEM LMS <stemappza@gmail.com>'

MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#P36
#p36
