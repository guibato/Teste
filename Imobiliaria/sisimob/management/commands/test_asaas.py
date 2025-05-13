import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis do .env

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY")
ASAAS_PAYMENTS_URL = os.getenv("ASAAS_PAYMENTS_URL")  # Ex: https://www.asaas.com/api/v3/payments
ASAAS_ID = "pay_sba011ha951bhmt8"

headers = {
    "Content-Type": "application/json",
    "access_token": ASAAS_API_KEY
}

url = f"{ASAAS_PAYMENTS_URL}/{ASAAS_ID}"
print(f"Testando URL: {url}")

response = requests.get(url, headers=headers)

print("Status code:", response.status_code)
print("Resposta:")
print(response.json())
