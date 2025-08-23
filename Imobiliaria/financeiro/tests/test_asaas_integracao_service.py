
import datetime
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

sys.modules.setdefault("requests", SimpleNamespace())
dummy_django_conf = SimpleNamespace(settings=SimpleNamespace())
sys.modules.setdefault("django", SimpleNamespace(conf=dummy_django_conf))
sys.modules.setdefault("django.conf", dummy_django_conf)
sys.modules.setdefault("sisimob", SimpleNamespace())
sys.modules.setdefault("sisimob.utils", SimpleNamespace())

from Imobiliaria.financeiro.services.cobranca.asaas_integracao_service import (
    AsaasIntegracaoService,
)


class FakeAsaasIntegracao(SimpleNamespace):
    def __init__(self, cobranca):
        super().__init__(cobranca=cobranca)
        self.save_called = False

    def save(self):
        self.save_called = True


class FakeCobranca(SimpleNamespace):
    def __init__(self, inquilino, valor_total=Decimal("100.00"),
                 vencimento=datetime.date(2024, 1, 1), descricao="Descricao"):
        super().__init__(
            inquilino=inquilino,
            valor_total=valor_total,
            data_vencimento=vencimento,
            descricao=descricao,
        )

    def gerar_descricao_automatica(self):
        return "Descricao automatica"


class FakeInquilino(SimpleNamespace):
    pass


def test_criar_cobranca_sucesso():
    inquilino = FakeInquilino(asaas_id="cus_1", nome="Fulano")
    cobranca = FakeCobranca(inquilino)
    integracao = FakeAsaasIntegracao(cobranca)

    calls = {}

    def fake_gerar(*args):
        calls["args"] = args
        return {
            "id": "pay_123",
            "bankSlipUrl": "http://boleto",
            
            "identificationField": "123456789",
            "status": "PENDING",
        }

    def fake_buscar(pagamento_id):
        calls["pix_id"] = pagamento_id
        return {
            "payload": "pix-copy",
            "qrCode": "pix-qrcode",
            "qrCodeUrl": "pix-url",
        }

    sys.modules["sisimob.utils.cobrancas_asaas"] = SimpleNamespace(
        gerar_cobranca=fake_gerar,
        buscar_pix_qrcode=fake_buscar,
    )

    resultado = AsaasIntegracaoService.criar_cobranca(
        integracao, {"observacoes": "Obs", "formas_pagamento": ["PIX", "BOLETO"]}
    )

    assert resultado["status"] == "success"
    assert integracao.asaas_id == "pay_123"
    assert integracao.boleto_url == "http://boleto"
    assert integracao.pix_copia_cola == "pix-copy"
    assert integracao.pix_qrcode == "pix-qrcode"
    assert integracao.pix_url == "pix-url"
    assert integracao.codigo_barras == "123456789"
    assert integracao.save_called is True

    assert calls["args"] == (
        "cus_1",
        100.0,
        "2024-01-01",
        "Fulano",
        "Descricao\n\nObs",
    )
    assert calls["pix_id"] == "pay_123"

def test_criar_cobranca_erro_integracao():
    inquilino = FakeInquilino(asaas_id="cus_1", nome="Fulano")
    cobranca = FakeCobranca(inquilino)
    integracao = FakeAsaasIntegracao(cobranca)

    def fake_gerar(*args):
        return {"erro": "falha"}

    sys.modules["sisimob.utils.cobrancas_asaas"] = SimpleNamespace(
        gerar_cobranca=fake_gerar,
        buscar_pix_qrcode=lambda _id: {},
    )

    resultado = AsaasIntegracaoService.criar_cobranca(integracao)

    assert resultado["status"] == "error"
    assert "Erro na integração" in resultado["erros"][0]
    assert not hasattr(integracao, "asaas_id")
    assert integracao.save_called is False
