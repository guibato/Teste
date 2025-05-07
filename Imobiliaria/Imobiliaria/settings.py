import os
from pathlib import Path

# Configurações Asaas
ASAAS_API_KEY = '$aact_hmlg_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6OjlmMjIzMzYzLTQyY2EtNGYwZS1hYmY4LWVhMGYyODU0YzQ0ZDo6JGFhY2hfMTJkOTc0YTAtZGExNC00MmExLTg1OWUtYTk3YzA3ZTYwMjgx'  # Sua chave de API do Asaas
ASAAS_API_URL = 'https://sandbox.asaas.com/api/v3'  # URL base da API
ASAAS_SANDBOX = True  # Defina como True para ambiente de teste

ZAPI_INSTANCE_ID = '3B230F028AA15052093F12A6A64DB285'
ZAPI_TOKEN = 'D1EF2C21320C6E36DACCB18C'
ZAPI_CLIENT_TOKEN = "F60efe793a1ab48d39ef6b31d14d7df00S"


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_URL = '/media/'  # URL base para arquivos
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
LANGUAGE_CODE = 'pt-br'
USE_L10N = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'mi@g_&0)j3-i$gc#@w9)zz-4u^!w7-x$*j_@142+tk7*&)=u6^'


DEBUG = True

ALLOWED_HOSTS = []

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
    'django_select2',
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

# Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

ROOT_URLCONF = 'Imobiliaria.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

USE_TZ = True
