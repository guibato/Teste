import os
import traceback
from typing import Any, Dict, Optional

import requests

ASAAS_API_KEY = os.getenv("ASAAS_API_KEY", "")
ASAAS_PAYMENTS_URL = os.getenv(
    "ASAAS_PAYMENTS_URL", "https://sandbox.asaas.com/api/v3/payments"
)


def _headers() -> Dict[str, str]:
    """Retorna os headers padrão para requisições ao Asaas."""
    return {"Content-Type": "application/json", "access_token": ASAAS_API_KEY}


def buscar_pix_qrcode(pagamento_id: str) -> Dict[str, Any]:
    """Busca o QR Code PIX de uma cobrança existente."""
    if not pagamento_id:
        return {"erro": "ID do pagamento não fornecido"}

    url = f"{ASAAS_PAYMENTS_URL}/{pagamento_id}/pixQrCode"
    try:
        response = requests.get(url, headers=_headers(), timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"erro": "Timeout na comunicação com o Asaas"}
    except requests.exceptions.ConnectionError:
        return {"erro": "Erro de conexão com o Asaas"}
    except Exception as e:  # pragma: no cover - falha inesperada
        traceback.print_exc()
        return {"erro": f"Erro na comunicação com o Asaas: {str(e)}"}


def gerar_cobranca(
    asaas_id: str,
    valor: float,
    vencimento: str,
    nome: str,
    descricao: Optional[str] = None,
) -> Dict[str, Any]:
    """Cria uma cobrança no Asaas para um cliente existente."""
    if not asaas_id:
        return {"erro": "ID do cliente Asaas não fornecido"}

    dados_cobranca = {
        "customer": asaas_id,
        "billingType": "BOLETO",
        "value": float(valor),
        "dueDate": vencimento,
        "description": descricao
        if descricao
        else f"Aluguel {vencimento[5:7]}/{vencimento[0:4]}",
        "name": nome,
        "interest": {"value": 1},
        "fine": {"value": 10, "type": "PERCENTAGE"},
        "paymentMethod": "BOLETO_PIX",
    }

    try:
        response = requests.post(
            ASAAS_PAYMENTS_URL, json=dados_cobranca, headers=_headers(), timeout=30
        )
        response.raise_for_status()
        dados = response.json()
        if "id" not in dados:
            return {"erro": dados}

        retorno: Dict[str, Any] = {
            "id": dados.get("id"),
            "bankSlipUrl": dados.get("bankSlipUrl"),
            "invoiceUrl": dados.get("invoiceUrl"),
            "identificationField": dados.get("identificationField"),
            "status": dados.get("status"),
            "pix": {
                "payload": dados.get("pix", {}).get("payload"),
                "qrCodeUrl": dados.get("pix", {}).get("qrCodeUrl"),
                "qrCode": dados.get("pix", {}).get("qrCode"),
            },
        }
        if dados.get("barCode"):
            retorno["barCode"] = dados.get("barCode")
        if dados.get("nossoNumero"):
            retorno["nossoNumero"] = dados.get("nossoNumero")
        return retorno
    except requests.exceptions.Timeout:
        return {"erro": "Timeout na comunicação com o Asaas"}
    except requests.exceptions.ConnectionError:
        return {"erro": "Erro de conexão com o Asaas"}
    except Exception as e:  # pragma: no cover - falha inesperada
        traceback.print_exc()
        return {"erro": f"Erro na comunicação com o Asaas: {str(e)}"}


def criar_cobranca_asaas(
    cliente: Any, valor: float, vencimento: str, descricao: Optional[str] = None
) -> Optional[str]:
    """Cria uma cobrança para um cliente usando seu ``asaas_id``.

    Args:
        cliente: Instância do cliente contendo ``asaas_id`` e nome.
        valor: Valor da cobrança.
        vencimento: Data de vencimento no formato ``YYYY-MM-DD``.
        descricao: Descrição opcional.

    Returns:
        O ID da cobrança criada ou ``None`` em caso de erro.
    """
    asaas_id = getattr(cliente, "asaas_id", None)
    if not asaas_id:
        return None

    resposta = gerar_cobranca(
        asaas_id=asaas_id,
        valor=valor,
        vencimento=vencimento,
        nome=getattr(cliente, "nome", ""),
        descricao=descricao,
    )
    if isinstance(resposta, dict) and resposta.get("id"):
        return resposta["id"]
    return None