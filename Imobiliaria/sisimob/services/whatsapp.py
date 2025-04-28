import requests
from django.conf import settings

def enviar_mensagem(numero, mensagem):
    url = f"https://api.z-api.io/instances/{settings.ZAPI_INSTANCE_ID}/token/{settings.ZAPI_TOKEN}/send-messages"
    payload = {
        "phone": numero,
        "message": mensagem
    }
    response = requests.post(url, json=payload)
    return response.json()