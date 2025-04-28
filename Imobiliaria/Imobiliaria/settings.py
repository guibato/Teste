import os
from pathlib import Path

# Configurações Asaas
ASAAS_API_KEY = "$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OmM0NmU2MWJmLTllYjctNGE0OC1hMDQ2LWY1NDU3YzhlMTY5ZTo6JGFhY2hfNzQ2MDIwYjktMGJmYi00ZGUwLWJhMDgtNGU0OTk4ZDA1NjNi"  # Sua chave de API do Asaas
ASAAS_API_URL = 'https://sandbox.asaas.com/api/v3'  # URL base da API
ASAAS_SANDBOX = True  # Defina como True para ambiente de teste
DEFAULT_CURRENCY = 'BRL'


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_URL = '/media/'  # URL base para arquivos
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
LANGUAGE_CODE = 'pt-br'
USE_L10N = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True




# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'mi@g_&0)j3-i$gc#@w9)zz-4u^!w7-x$*j_@142+tk7*&)=u6^'

ZAPI_INSTANCE_ID = os.getenv('3B230F028AA15052093F12A6A64DB285')
ZAPI_TOKEN = os.getenv('D1EF2C21320C6E36DACCB18C')
ZAPI_BASE_URL = f'https://api.z-api.io/instances/3B230F028AA15052093F12A6A64DB285/token/D1EF2C21320C6E36DACCB18C'
ZAPI_CLIENT_TOKEN = "F60efe793a1ab48d39ef6b31d14d7df00S"

DEBUG = True

ALLOWED_HOSTS = []
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"
STATIC_ROOT = BASE_DIR / 'staticfiles'


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'sisimob',
    'imobiliaria',
    'django.contrib.humanize',
    'crispy_forms',
    'crispy_tailwind',
    'djmoney',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Imobiliaria.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Add a project-level templates directory if needed
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'Imobiliaria.wsgi.application'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configurações de arquivos estáticos
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    "C:/Users/guilh/OneDrive/Pessoal/Documentos/GitHub/Teste/imobiliaria/sisimob/static",
    
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}