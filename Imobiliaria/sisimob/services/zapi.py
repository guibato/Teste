import requests
from django.conf import settings


def enviar_mensagem(numero, mensagem):
    url = f"{settings.ZAPI_BASE_URL}/send-text"
    payload = {
        "phone": numero,
        "message": mensagem
    }
    headers = {
        "Content-Type": "application/json",
        "client-token": settings.ZAPI_CLIENT_TOKEN  # Adicione essa linha
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def enviar_midia(numero, link_arquivo, legenda=""):
    """
    Envia uma mídia (PDF, imagem, áudio, etc.) via Z-API.
    """
    url = f"{settings.ZAPI_BASE_URL}/send-file"
    payload = {
        "phone": numero,
        "caption": legenda,
        "file": link_arquivo  # URL pública para o arquivo
    }
    response = requests.post(url, json=payload)
    return response.json()
