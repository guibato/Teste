from django.apps import apps
from django.db.models import Sum


class ContratoFinanceiroService:
    """Serviços financeiros relacionados ao contrato."""

    @staticmethod
    def obter_detalhes_contrato(contrato):
        """Obtém dados financeiros detalhados de um contrato."""
        Cobranca = apps.get_model("financeiro", "Cobranca")

        try:
            cobrancas = contrato.cobrancas_financeiro.all().order_by('-data_vencimento')
        except AttributeError:
            try:
                cobrancas = contrato.cobrancas.all().order_by('-data_vencimento')
            except AttributeError:
                cobrancas = Cobranca.objects.none()

        try:
            repasses = contrato.repasses.all().order_by('-data_repasse')
        except AttributeError:
            try:
                repasses = contrato.repasse_set.all().order_by('-data_repasse')
            except AttributeError:
                repasses = []

        cobrancas_pagas = cobrancas.filter(status='paga') if cobrancas is not None else Cobranca.objects.none()
        cobrancas_pendentes = cobrancas.filter(status='pendente') if cobrancas is not None else Cobranca.objects.none()
        cobrancas_atrasadas = cobrancas.filter(status='atrasada') if cobrancas is not None else Cobranca.objects.none()

        total_pago = cobrancas_pagas.aggregate(total=Sum('valor_total'))['total'] or 0
        total_pendente = cobrancas_pendentes.aggregate(total=Sum('valor_total'))['total'] or 0
        total_atrasado = cobrancas_atrasadas.aggregate(total=Sum('valor_total'))['total'] or 0

        return {
            'cobrancas': cobrancas,
            'repasses': repasses,
            'cobrancas_pagas': cobrancas_pagas,
            'cobrancas_pendentes': cobrancas_pendentes,
            'cobrancas_atrasadas': cobrancas_atrasadas,
            'total_cobrancas': cobrancas.count() if cobrancas is not None else 0,
            'total_pago': total_pago,
            'total_pendente': total_pendente,
            'total_atrasado': total_atrasado,
            'total_geral': total_pago + total_pendente + total_atrasado,
            'ultimas_cobrancas': cobrancas[:5] if cobrancas is not None else [],
        }

    @staticmethod
    def obter_dashboard_contrato(contrato, ano_selecionado=None, status_selecionado=None):
        """Obtém dados para o dashboard financeiro do contrato."""
        Cobranca = apps.get_model("financeiro", "Cobranca")
        Despesa = apps.get_model("financeiro", "Despesa")

        cobrancas = Cobranca.objects.filter(contrato=contrato)
        if ano_selecionado:
            cobrancas = cobrancas.filter(ano_referencia=ano_selecionado)
        if status_selecionado:
            cobrancas = cobrancas.filter(status=status_selecionado)

        despesas = Despesa.objects.filter(contrato=contrato)

        cobrancas_pagas = cobrancas.filter(status='paga')

        total_receitas = sum(c.valor_aluguel for c in cobrancas_pagas)
        total_taxa_admin = sum(c.valor_administracao for c in cobrancas_pagas)
        total_repasse = sum(c.valor_liquido for c in cobrancas_pagas)

        total_despesas_apropriadas = 0
        for cobranca in cobrancas_pagas:
            try:
                despesas_cobranca = cobranca.get_despesas_cobranca()
                total_despesas_apropriadas += sum(
                    d.calcular_valor_parcela() for d in despesas_cobranca
                )
            except Exception:
                pass

        anos_disponiveis = cobrancas.dates('data_vencimento', 'year', order='DESC')

        saldo = total_receitas - total_despesas_apropriadas

        return {
            'cobrancas': cobrancas.order_by('data_vencimento'),
            'despesas': despesas.order_by('-data_inicio'),
            'cobrancas_pagas': cobrancas_pagas,
            'total_receitas': total_receitas,
            'total_despesas': total_despesas_apropriadas,
            'total_despesas_apropriadas': total_despesas_apropriadas,
            'total_taxa_admin': total_taxa_admin,
            'total_repasse': total_repasse,
            'saldo': saldo,
            'saldo_positivo': saldo >= 0,
            'lucro_administradora': total_taxa_admin,
            'anos_disponiveis': anos_disponiveis,
        }