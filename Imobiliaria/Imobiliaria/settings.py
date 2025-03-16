import os
from pathlib import Path


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