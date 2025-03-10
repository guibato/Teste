import os
from django.core.wsgi import get_wsgi_application

# Define o módulo de configurações do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Imobiliaria.settings')

# Cria a aplicação WSGI
application = get_wsgi_application()