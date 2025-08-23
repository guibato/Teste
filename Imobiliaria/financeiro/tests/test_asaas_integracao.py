from django.test import TestCase
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch

from Imobiliaria.financeiro.models.cobranca import Cobranca, AsaasIntegracao
from Imobiliaria.sisimob.models import Cliente, Imovel, Contrato
from Imobiliaria.financeiro.services.cobranca.asaas_integracao_service import AsaasIntegracaoService


class AsaasIntegracaoServiceTests(TestCase):
    def setUp(self):
        patcher_cadastrar = patch(
            'sisimob.utils.integracao_asaas.cadastrar_cliente_no_asaas',
            return_value='cli_mock'
        )
        patcher_atualizar = patch(
            'sisimob.utils.integracao_asaas.atualizar_cliente_no_asaas',
            return_value=True
        )
        self.addCleanup(patcher_cadastrar.stop)
        self.addCleanup(patcher_atualizar.stop)
        patcher_cadastrar.start()
        patcher_atualizar.start()

        # Criar clientes
        self.proprietario = Cliente.objects.create(
            tipo_pessoa='F', tipo='Proprietario', nome='Proprietario',
            cep='12345-000', endereco='Rua 1', numero='1', cidade='Cidade', estado='SP'
        )
        self.inquilino = Cliente.objects.create(
            tipo_pessoa='F', tipo='Inquilino', nome='Inquilino',
            cep='12345-000', endereco='Rua 1', numero='1', cidade='Cidade', estado='SP',
            email='inquilino@example.com', CPF='123.456.789-00', asaas_id='cli_1'
        )

        # Criar imóvel
        self.imovel = Imovel.objects.create(
            cep='12345-000', endereco='Rua 1', numero='1', cidade='Cidade', estado='SP'
        )

        # Criar contrato
        self.contrato = Contrato.objects.create(
            tipo='residencial', imovel=self.imovel,
            data_inicio=date.today(), data_fim=date.today() + timedelta(days=30),
            fator_reajuste='IPCA', multa_contratual='3MPR',
            tipo_pagamento='despesas_separadas', valor_base=Decimal('1000.00'),
            tipo_taxa='percentual', valor_taxa_administracao_percentual=Decimal('10.00'),
            dia_pagamento=5, garantia='FIADOR'
        )
        self.contrato.proprietario.add(self.proprietario)
        self.contrato.inquilino.add(self.inquilino)

        # Criar cobrança
        self.cobranca = Cobranca.objects.create(
            contrato=self.contrato,
            mes_referencia=1,
            ano_referencia=2024,
            valor=Decimal('1000.00'),
            numero_cobranca='1',
            data_vencimento=date.today(),
            detalhes_calculo={'valor_base': '1000.00', 'valor_despesas': '0.00'}
        )

        # Integração Asaas
        self.integracao = AsaasIntegracao.objects.create(cobranca=self.cobranca, asaas_id='tmp')

    @patch('sisimob.utils.cobrancas_asaas.gerar_cobranca')
    def test_criar_cobranca_salva_opcoes_envio(self, mock_gerar):
        mock_gerar.return_value = {
            'id': 'pay_1',
            'bankSlipUrl': 'http://boleto',
            'pixCopiaeCola': 'pixcode',
            'pixQrCodeBase64': 'pixqrcode',
            'pixUrl': 'http://pix',
            'barCode': '123',
            'invoiceUrl': 'http://fatura',
            'status': 'PENDING'
        }
        opcoes = {
            'formas_pagamento': ['PIX', 'BOLETO'],
            'enviar_por_email': False,
            'enviar_por_whatsapp': True
        }

        resultado = AsaasIntegracaoService.criar_cobranca(self.integracao, opcoes)
        self.integracao.refresh_from_db()

        self.assertEqual(resultado['status'], 'success')
        self.assertEqual(self.integracao.formas_pagamento, ['PIX', 'BOLETO'])
        self.assertFalse(self.integracao.envio_email)
        self.assertTrue(self.integracao.envio_whatsapp)
        self.assertEqual(self.integracao.fatura_url, 'http://fatura')

    @patch('financeiro.models.cobranca.Cobranca.marcar_como_paga')
    def test_processar_webhook_registra_evento(self, mock_marcar):
        def marcar_stub(data_pagamento):
            self.cobranca.status = 'paga'
            self.cobranca.data_pagamento = data_pagamento
            self.cobranca.save(update_fields=['status', 'data_pagamento'])
            return True

        mock_marcar.side_effect = marcar_stub

        dados = {
            'event': 'PAYMENT_RECEIVED',
            'payment': {'dateReceived': '2024-01-10', 'status': 'CONFIRMED'}
        }

        AsaasIntegracaoService.processar_webhook(self.integracao, dados)
        self.integracao.refresh_from_db()
        self.cobranca.refresh_from_db()

        self.assertEqual(len(self.integracao.webhooks_recebidos), 1)
        self.assertEqual(self.integracao.webhooks_recebidos[0]['evento'], 'PAYMENT_RECEIVED')
        self.assertEqual(self.cobranca.status, 'paga')
        self.assertEqual(self.cobranca.data_pagamento, date(2024, 1, 10))