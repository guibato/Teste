
import requests
from django.conf import settings
import os

def enviar_mensagem(numero, mensagem):
    ZAPI_INSTANCE_ID = os.getenv('ZAPI_INSTANCE_ID')
    ZAPI_TOKEN = os.getenv('ZAPI_TOKEN')
    ZAPI_CLIENT_TOKEN = os.getenv('ZAPI_CLIENT_TOKEN')
    url = f"https://api.z-api.io/instances/{ZAPI_INSTANCE_ID}/token/{ZAPI_TOKEN}/send-messages"
    payload = {
        "phone": numero,
        "message": mensagem
    }

    headers = {
        "Content-Type": "application/json",
        "client-token": ZAPI_CLIENT_TOKEN  # Adicione essa linha
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
    