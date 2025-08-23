# conftest.py (na raiz do projeto)
import os, sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
# garante que a raiz (onde fica a pasta Imobiliaria/) está no sys.path
if str(BASE_DIR) not in map(str, sys.path):
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Imobiliaria.settings")

import django
django.setup()
