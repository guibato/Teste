import datetime
from decimal import Decimal
from django.apps import apps


class CobrancaCalculadoraService:
    """Service para cálculos de valores de cobranças"""
    
    @staticmethod
    def calcular_valor_aluguel(contrato, mes=None, ano=None):
        if not contrato:
            return Decimal('0.00')
    
        # Se tem mês/ano, usar valor reajustado
        if mes and ano:
            from financeiro.views.cobranca_views import obter_valor_atual_contrato
            valor_reajustado = obter_valor_atual_contrato(contrato, mes, ano)
            return Decimal(str(valor_reajustado))
        
        # Fallback para valor base
        valor_base = getattr(contrato, 'valor_base', Decimal('0.00'))
        valor_aluguel = getattr(contrato, 'valor_aluguel', valor_base)
        return Decimal(str(valor_aluguel))
    

    
    @staticmethod
    def buscar_despesas_periodo(contrato, mes, ano):
        """
        Busca despesas ativas para o contrato no período especificado
        """
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano, mes, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            # Filtrar apenas despesas ativas no período
            despesas_ativas = [
                despesa for despesa in despesas 
                if hasattr(despesa, 'parcela_ativa_em_data') and despesa.parcela_ativa_em_data(data_referencia)
            ]
            
            # Se método não existir, usar todas as despesas ativas
            if not despesas_ativas:
                despesas_ativas = list(despesas)
            
            return despesas_ativas
            
        except LookupError:
            # Modelo Despesa não encontrado
            return []
    
    @staticmethod
    def calcular_despesas_periodo(contrato, mes_referencia, ano_referencia):
        """
        CORRIGIDO: Calcula o valor das despesas APENAS do período específico.
        Fórmula: + despesas do inquilino - despesas do proprietário/imobiliária
        """
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano_referencia, mes_referencia, 1)
            
            # Buscar todas as despesas ativas
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            # CORRIGIDO: Filtrar por período usando parcela_ativa_em_data
            despesas_periodo = []
            for despesa in despesas:
                if hasattr(despesa, 'parcela_ativa_em_data'):
                    if despesa.parcela_ativa_em_data(data_referencia):
                        despesas_periodo.append(despesa)
                # Se não tem o método, incluir apenas se data_inicio está no período
                elif hasattr(despesa, 'data_inicio'):
                    if (despesa.data_inicio.year == ano_referencia and 
                        despesa.data_inicio.month == mes_referencia):
                        despesas_periodo.append(despesa)
            
            # Separar por quem paga
            valor_inquilino = Decimal('0.00')
            valor_credito = Decimal('0.00')
            
            for despesa in despesas_periodo:
                if hasattr(despesa, 'calcular_valor_parcela'):
                    valor_despesa = despesa.calcular_valor_parcela()
                else:
                    valor_despesa = getattr(despesa, 'valor_total', Decimal('0.00'))
                
                # Lógica de crédito/débito
                if despesa.paga_por == 'inquilino':
                    valor_inquilino += valor_despesa  # DÉBITO (soma)
                elif despesa.paga_por in ['proprietario', 'imobiliaria']:
                    valor_credito += valor_despesa    # CRÉDITO (subtrai)
            
            # Valor final: débitos - créditos
            valor_final = valor_inquilino - valor_credito
            
            return valor_final
            
        except LookupError:
            return Decimal('0.00')

    @staticmethod
    def get_despesas_periodo_info(contrato, mes_referencia, ano_referencia):
        """
        CORRIGIDO: Retorna informações das despesas APENAS do período específico
        """
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano_referencia, mes_referencia, 1)
            
            # Buscar despesas ativas
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            # CORRIGIDO: Filtrar por período usando parcela_ativa_em_data
            despesas_periodo = []
            for despesa in despesas:
                if hasattr(despesa, 'parcela_ativa_em_data'):
                    if despesa.parcela_ativa_em_data(data_referencia):
                        despesas_periodo.append(despesa)
                # Se não tem o método, incluir apenas se data_inicio está no período
                elif hasattr(despesa, 'data_inicio'):
                    if (despesa.data_inicio.year == ano_referencia and 
                        despesa.data_inicio.month == mes_referencia):
                        despesas_periodo.append(despesa)
            
            debitos_inquilino = []
            creditos_proprietario = []
            total_debitos = Decimal('0.00')
            total_creditos = Decimal('0.00')
            
            for despesa in despesas_periodo:
                # Calcular valor
                if hasattr(despesa, 'calcular_valor_parcela'):
                    valor = despesa.calcular_valor_parcela()
                else:
                    valor = getattr(despesa, 'valor_total', Decimal('0.00'))
                
                # Obter nome do tipo
                tipo_nome = "Despesa"
                if hasattr(despesa, 'tipo') and despesa.tipo:
                    tipo_nome = getattr(despesa.tipo, 'nome', 'Despesa')
                
                # Criar item
                item = {
                    'id': despesa.id,
                    'tipo': tipo_nome,
                    'descricao': getattr(despesa, 'descricao', None) or f"Despesa de {tipo_nome}",
                    'valor': float(valor),
                    'paga_por': despesa.paga_por,
                    'data_inicio': despesa.data_inicio.strftime('%Y-%m-%d') if hasattr(despesa, 'data_inicio') else None
                }
                
                # Classificar como débito ou crédito
                if despesa.paga_por == 'inquilino':
                    debitos_inquilino.append(item)
                    total_debitos += valor
                elif despesa.paga_por in ['proprietario', 'imobiliaria']:
                    creditos_proprietario.append(item)
                    total_creditos += valor
            
            return {
                'debitos_inquilino': debitos_inquilino,
                'creditos_proprietario': creditos_proprietario,
                'total_debitos': float(total_debitos),
                'total_creditos': float(total_creditos),
                'periodo_filtrado': f"{mes_referencia:02d}/{ano_referencia}",
                'despesas_filtradas': len(despesas_periodo),
                'despesas_totais_ativas': despesas.count()
            }
            
        except LookupError:
            return {
                'debitos_inquilino': [],
                'creditos_proprietario': [],
                'total_debitos': 0.0,
                'total_creditos': 0.0,
                'periodo_filtrado': f"{mes_referencia:02d}/{ano_referencia}",
                'despesas_filtradas': 0,
                'despesas_totais_ativas': 0
            }
    @staticmethod
    def calcular_valor_completo(contrato, mes_referencia, ano_referencia):
        """
        NOVA FUNÇÃO: Calcula o valor total da cobrança com a lógica correta
        """
        # Valor base do contrato
        valor_base = CobrancaCalculadoraService.calcular_valor_aluguel(contrato, mes_referencia, ano_referencia)
        
        # Calcular despesas (já com a lógica de crédito/débito)
        valor_despesas = CobrancaCalculadoraService.calcular_despesas_periodo(
            contrato, mes_referencia, ano_referencia
        )
        
        # Valor total
        valor_total = valor_base + valor_despesas
        
        return {
            'valor_base': valor_base,
            'valor_despesas': valor_despesas,
            'valor_total': valor_total,
            'detalhes': CobrancaCalculadoraService.get_despesas_periodo_info(
                contrato, mes_referencia, ano_referencia
            )
        }
    
    # === MÉTODOS ORIGINAIS (mantidos para compatibilidade) ===
    
    @staticmethod
    def calcular_valor_despesas(despesas):
        """
        MÉTODO ORIGINAL: Calcula o valor total das despesas
        """
        if not despesas:
            return Decimal('0.00')
        
        valor_total = Decimal('0.00')
        for despesa in despesas:
            if hasattr(despesa, 'calcular_valor_parcela'):
                valor_total += despesa.calcular_valor_parcela()
            else:
                # Fallback se método não existir
                valor_total += getattr(despesa, 'valor_total', Decimal('0.00'))
        
        return valor_total
    
    @staticmethod
    def calcular_valor_total(valor_aluguel, despesas):
        """
        MÉTODO ORIGINAL: Calcula valor total: aluguel + despesas
        """
        valor_aluguel = Decimal(str(valor_aluguel or 0))
        valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
        
        return valor_aluguel + valor_despesas
    
    @staticmethod
    def calcular_taxa_administracao(contrato, valor_aluguel):
        """
        Calcula valor da taxa de administração
        """
        if not contrato or not valor_aluguel:
            return Decimal('0.00')
        
        try:
            tipo_taxa = getattr(contrato, 'tipo_taxa', None)
            
            if tipo_taxa == 'percentual':
                percentual = getattr(contrato, 'valor_taxa_administracao_percentual', Decimal('0.00'))
                if percentual:
                    return (Decimal(str(valor_aluguel)) * percentual / Decimal('100')).quantize(Decimal('0.01'))
            
            elif tipo_taxa == 'fixo':
                valor_fixo = getattr(contrato, 'valor_taxa_administracao_fixo', Decimal('0.00'))
                return Decimal(str(valor_fixo or 0))
            
        except (AttributeError, TypeError):
            pass
        
        return Decimal('0.00')
    
    @staticmethod
    def calcular_valor_repasse(cobranca):
        """
        Calcula valor do repasse para o proprietário
        """
        if not cobranca:
            return Decimal('0.00')
        
        valor_total = cobranca.valor_total
        taxa_administracao = getattr(cobranca, 'calcular_valor_administracao', lambda: Decimal('0.00'))()
        
        # Buscar despesas pagas pelo proprietário
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(cobranca.ano_referencia, cobranca.mes_referencia, 1)
            
            despesas_proprietario = Despesa.objects.filter(
                contrato=cobranca.contrato,
                is_ativa=True,
                paga_por='proprietario'
            )
            
            valor_despesas_proprietario = Decimal('0.00')
            for d in despesas_proprietario:
                if hasattr(d, 'parcela_ativa_em_data') and d.parcela_ativa_em_data(data_referencia):
                    if hasattr(d, 'calcular_valor_parcela'):
                        valor_despesas_proprietario += d.calcular_valor_parcela()
                    else:
                        valor_despesas_proprietario += getattr(d, 'valor_total', Decimal('0.00'))
            
        except LookupError:
            valor_despesas_proprietario = Decimal('0.00')
        
        valor_repasse = valor_total - taxa_administracao - valor_despesas_proprietario
        return max(valor_repasse, Decimal('0.00'))  # Não permitir repasse negativo


    
    @staticmethod
    def calcular_valor_aluguel(contrato, mes=None, ano=None):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        if not contrato:
            return Decimal('0.00')
    
        # Se tem mês/ano, usar valor reajustado
        if mes and ano:
            from financeiro.views.cobranca_views import obter_valor_atual_contrato
            valor_reajustado = obter_valor_atual_contrato(contrato, mes, ano)
            return Decimal(str(valor_reajustado))
        
        # Fallback para valor base
        valor_base = getattr(contrato, 'valor_base', Decimal('0.00'))
        valor_aluguel = getattr(contrato, 'valor_aluguel', valor_base)
        return Decimal(str(valor_aluguel))

    @staticmethod
    def buscar_despesas_periodo(contrato, mes, ano):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano, mes, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            # Filtrar apenas despesas ativas no período
            despesas_ativas = [
                despesa for despesa in despesas 
                if hasattr(despesa, 'parcela_ativa_em_data') and despesa.parcela_ativa_em_data(data_referencia)
            ]
            
            # Se método não existir, usar todas as despesas ativas
            if not despesas_ativas:
                despesas_ativas = list(despesas)
            
            return despesas_ativas
            
        except LookupError:
            return []

    @staticmethod
    def calcular_valor_despesas(despesas):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        if not despesas:
            return Decimal('0.00')
        
        valor_total = Decimal('0.00')
        for despesa in despesas:
            if hasattr(despesa, 'calcular_valor_parcela'):
                valor_total += despesa.calcular_valor_parcela()
            else:
                valor_total += getattr(despesa, 'valor_total', Decimal('0.00'))
        
        return valor_total

    @staticmethod
    def calcular_valor_total(valor_aluguel, despesas):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        valor_aluguel = Decimal(str(valor_aluguel or 0))
        valor_despesas = CobrancaCalculadoraService.calcular_valor_despesas(despesas)
        
        return valor_aluguel + valor_despesas

    # === NOVOS MÉTODOS PARA CÁLCULO COM INCIDÊNCIA DE TAXA ===
    
    @staticmethod
    def calcular_composicao_com_incidencia(contrato, mes_referencia, ano_referencia):
        """
        🆕 NOVO: Calcula composição separando valores com/sem incidência de taxa
        
        Returns:
            dict: {
                'valor_total_cobranca': Decimal,
                'valor_com_incidencia': Decimal,  # Base para cálculo de taxa admin
                'valor_sem_incidencia': Decimal,  # Isento de taxa admin
                'valor_taxa_administrativa': Decimal,
                'valor_liquido_repasse': Decimal,
                'componentes': [...]  # Detalhamento
            }
        """
        print(f"🧮 Calculando composição com incidência para contrato #{contrato.id} - {mes_referencia:02d}/{ano_referencia}")
        
        # 1. ALUGUEL (sempre com incidência)
        valor_aluguel = CobrancaCalculadoraService.calcular_valor_aluguel(
            contrato, mes_referencia, ano_referencia
        )
        print(f"   💰 Aluguel: R$ {valor_aluguel:.2f} (com incidência)")
        
        # 2. DESPESAS SEPARADAS POR INCIDÊNCIA
        despesas_info = CobrancaCalculadoraService._analisar_despesas_com_incidencia(
            contrato, mes_referencia, ano_referencia
        )
        
        # 3. TOTAIS
        valor_com_incidencia = valor_aluguel + despesas_info['valor_com_incidencia']
        valor_sem_incidencia = despesas_info['valor_sem_incidencia']
        valor_total_cobranca = valor_com_incidencia + valor_sem_incidencia
        
        print(f"   📊 Com incidência: R$ {valor_com_incidencia:.2f}")
        print(f"   🆓 Sem incidência: R$ {valor_sem_incidencia:.2f}")
        print(f"   💸 Total cobrança: R$ {valor_total_cobranca:.2f}")
        
        # 4. TAXA ADMINISTRATIVA
        taxa_admin_percentual = CobrancaCalculadoraService._obter_taxa_admin_contrato(contrato)
        valor_taxa_administrativa = valor_com_incidencia * (taxa_admin_percentual / 100)
        
        print(f"   🏛️ Taxa admin ({taxa_admin_percentual}%): R$ {valor_taxa_administrativa:.2f}")
        
        # 5. REPASSE LÍQUIDO
        valor_liquido_repasse = valor_total_cobranca - valor_taxa_administrativa
        
        print(f"   🎯 Repasse líquido: R$ {valor_liquido_repasse:.2f}")
        
        # 6. COMPONENTES DETALHADOS
        componentes = [
            {
                'tipo': 'aluguel',
                'descricao': 'Valor do aluguel',
                'valor': valor_aluguel,
                'tem_incidencia_taxa': True,
                'valor_taxa_admin': valor_aluguel * (taxa_admin_percentual / 100),
                'valor_liquido': valor_aluguel * (1 - taxa_admin_percentual / 100),
                'observacoes': 'Aluguel sempre tem incidência de taxa administrativa'
            }
        ] + despesas_info['componentes_detalhados']
        
        return {
            'valor_total_cobranca': valor_total_cobranca,
            'valor_com_incidencia': valor_com_incidencia,
            'valor_sem_incidencia': valor_sem_incidencia,
            'taxa_admin_percentual': taxa_admin_percentual,
            'valor_taxa_administrativa': valor_taxa_administrativa,
            'valor_liquido_repasse': valor_liquido_repasse,
            'componentes': componentes,
            'resumo_calculo': {
                'formula': f"R$ {valor_total_cobranca:.2f} (total) - R$ {valor_taxa_administrativa:.2f} (taxa) = R$ {valor_liquido_repasse:.2f} (repasse)",
                'base_taxa': f"Taxa de {taxa_admin_percentual}% sobre R$ {valor_com_incidencia:.2f}",
                'isencao': f"R$ {valor_sem_incidencia:.2f} isentos de taxa administrativa"
            }
        }

    @staticmethod
    def _analisar_despesas_com_incidencia(contrato, mes_referencia, ano_referencia):
        """
        🔍 Analisa despesas separando por incidência de taxa administrativa
        """
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano_referencia, mes_referencia, 1)
            
            # Buscar despesas ativas no período
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            # Filtrar por período
            despesas_periodo = [
                d for d in despesas 
                if hasattr(d, 'parcela_ativa_em_data') and d.parcela_ativa_em_data(data_referencia)
            ]
            
            print(f"   🔍 Analisando {len(despesas_periodo)} despesas do período")
            
            valor_com_incidencia = Decimal('0.00')
            valor_sem_incidencia = Decimal('0.00')
            componentes_detalhados = []
            
            for despesa in despesas_periodo:
                # Calcular valor da despesa
                if hasattr(despesa, 'calcular_valor_parcela'):
                    valor_despesa = despesa.calcular_valor_parcela()
                else:
                    valor_despesa = getattr(despesa, 'valor_total', Decimal('0.00'))
                
                # Apenas despesas pagas pelo inquilino entram na cobrança
                if despesa.paga_por != 'inquilino':
                    print(f"     ⏭️ {despesa}: paga por {despesa.paga_por} - ignorada na cobrança")
                    continue
                
                # Verificar incidência de taxa administrativa
                tem_incidencia = CobrancaCalculadoraService._despesa_tem_incidencia_taxa(despesa)
                
                # Separar valores
                if tem_incidencia:
                    valor_com_incidencia += valor_despesa
                    print(f"     ✅ {despesa}: R$ {valor_despesa:.2f} (COM taxa)")
                else:
                    valor_sem_incidencia += valor_despesa
                    print(f"     🆓 {despesa}: R$ {valor_despesa:.2f} (SEM taxa)")
                
                # Taxa administrativa (se aplicável)
                taxa_admin = CobrancaCalculadoraService._obter_taxa_admin_contrato(contrato)
                valor_taxa_admin_despesa = valor_despesa * (taxa_admin / 100) if tem_incidencia else Decimal('0.00')
                valor_liquido_despesa = valor_despesa - valor_taxa_admin_despesa
                
                # Adicionar ao detalhamento
                tipo_nome = getattr(despesa.tipo, 'nome', 'Despesa') if hasattr(despesa, 'tipo') else 'Despesa'
                
                componentes_detalhados.append({
                    'tipo': 'despesa',
                    'nome_tipo': tipo_nome,
                    'descricao': getattr(despesa, 'descricao', None) or f"{tipo_nome}",
                    'valor': valor_despesa,
                    'tem_incidencia_taxa': tem_incidencia,
                    'valor_taxa_admin': valor_taxa_admin_despesa,
                    'valor_liquido': valor_liquido_despesa,
                    'paga_por': despesa.paga_por,
                    'observacoes': CobrancaCalculadoraService._gerar_observacao_despesa(despesa)
                })
            
            return {
                'valor_com_incidencia': valor_com_incidencia,
                'valor_sem_incidencia': valor_sem_incidencia,
                'componentes_detalhados': componentes_detalhados,
                'total_despesas_analisadas': len(despesas_periodo)
            }
            
        except LookupError:
            print("   ❌ Modelo Despesa não encontrado")
            return {
                'valor_com_incidencia': Decimal('0.00'),
                'valor_sem_incidencia': Decimal('0.00'),
                'componentes_detalhados': [],
                'total_despesas_analisadas': 0
            }

    @staticmethod
    def _despesa_tem_incidencia_taxa(despesa):
        """
        🔍 Determina se uma despesa tem incidência de taxa administrativa
        
        LÓGICA:
        1. Usar campo incidencia_taxa_admin da despesa
        2. Se não definido, usar configuração do contrato (se existir)
        3. Fallback: sem incidência
        """
        # Verificar campo da própria despesa
        if hasattr(despesa, 'incidencia_taxa_admin'):
            if despesa.incidencia_taxa_admin == 'sim':
                return True
            elif despesa.incidencia_taxa_admin == 'nao':
                return False
            # Se for 'parcial', considerar como 'sim' por enquanto
            elif despesa.incidencia_taxa_admin == 'parcial':
                return True
        
        # TODO: Implementar lógica por contrato quando definir o campo
        # if hasattr(despesa.contrato, 'despesas_tem_incidencia_taxa'):
        #     return despesa.contrato.despesas_tem_incidencia_taxa
        
        # Fallback: sem incidência
        return False

    @staticmethod
    def _obter_taxa_admin_contrato(contrato):
        """🏛️ Obtém taxa de administração do contrato"""
        if hasattr(contrato, 'valor_taxa_administracao_percentual'):
            taxa = contrato.valor_taxa_administracao_percentual
            if taxa and taxa > 0:
                return taxa
        
        # Fallback padrão
        return Decimal('8.00')

    @staticmethod
    def _gerar_observacao_despesa(despesa):
        """📝 Gera observação explicativa sobre a despesa"""
        tem_incidencia = CobrancaCalculadoraService._despesa_tem_incidencia_taxa(despesa)
        
        if hasattr(despesa, 'incidencia_taxa_admin'):
            if despesa.incidencia_taxa_admin == 'sim':
                return "Despesa configurada com incidência de taxa administrativa"
            elif despesa.incidencia_taxa_admin == 'nao':
                return "Despesa configurada sem incidência de taxa administrativa"
            elif despesa.incidencia_taxa_admin == 'parcial':
                return "Despesa com incidência parcial (tratada como total por enquanto)"
        
        return "Incidência determinada por configuração padrão"

    # === MÉTODO PARA ATUALIZAR COBRANÇA EXISTENTE ===
    
    @staticmethod
    def recalcular_detalhes_cobranca(cobranca):
        """
        🔄 Recalcula detalhes de uma cobrança existente com a nova lógica
        
        Use para atualizar cobranças já criadas (como as de 07/2025)
        """
        print(f"🔄 Recalculando cobrança #{cobranca.id}")
        
        # Calcular nova composição
        composicao = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
            cobranca.contrato, 
            cobranca.mes_referencia, 
            cobranca.ano_referencia
        )
        
        # Atualizar detalhes_calculo com nova estrutura
        novos_detalhes = {
            **cobranca.detalhes_calculo,  # Manter dados antigos
            'composicao_com_incidencia': {
                'valor_total_cobranca': float(composicao['valor_total_cobranca']),
                'valor_com_incidencia': float(composicao['valor_com_incidencia']),
                'valor_sem_incidencia': float(composicao['valor_sem_incidencia']),
                'taxa_admin_percentual': float(composicao['taxa_admin_percentual']),
                'valor_taxa_administrativa': float(composicao['valor_taxa_administrativa']),
                'valor_liquido_repasse': float(composicao['valor_liquido_repasse']),
                'componentes': [
                    {
                        **comp,
                        'valor': float(comp['valor']),
                        'valor_taxa_admin': float(comp.get('valor_taxa_admin', 0)),
                        'valor_liquido': float(comp.get('valor_liquido', 0))
                    }
                    for comp in composicao['componentes']
                ],
                'data_recalculo': datetime.datetime.now().isoformat(),
                'metodo': 'recalculo_com_incidencia_taxa'
            }
        }
        
        cobranca.detalhes_calculo = novos_detalhes
        cobranca.save(update_fields=['detalhes_calculo'])
        
        print(f"✅ Cobrança #{cobranca.id} recalculada com nova lógica")
        
        return composicao

    # === MÉTODO ORIGINAL MELHORADO ===
    
    @staticmethod
    def calcular_valor_completo(contrato, mes_referencia, ano_referencia):
        """
        MÉTODO ORIGINAL com nova lógica opcional
        
        Mantém compatibilidade mas adiciona informações de incidência
        """
        # Cálculo tradicional (mantido)
        valor_base = CobrancaCalculadoraService.calcular_valor_aluguel(contrato, mes_referencia, ano_referencia)
        valor_despesas = CobrancaCalculadoraService.calcular_despesas_periodo(contrato, mes_referencia, ano_referencia)
        valor_total = valor_base + valor_despesas
        
        # Nova informação de incidência
        composicao_incidencia = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
            contrato, mes_referencia, ano_referencia
        )
        
        return {
            # Dados originais (compatibilidade)
            'valor_base': valor_base,
            'valor_despesas': valor_despesas,
            'valor_total': valor_total,
            'detalhes': CobrancaCalculadoraService.get_despesas_periodo_info(contrato, mes_referencia, ano_referencia),
            
            # Novos dados com incidência
            'composicao_incidencia': composicao_incidencia
        }

    # === MÉTODOS ORIGINAIS MANTIDOS ===
    
    @staticmethod
    def calcular_despesas_periodo(contrato, mes_referencia, ano_referencia):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano_referencia, mes_referencia, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            despesas_periodo = []
            for despesa in despesas:
                if hasattr(despesa, 'parcela_ativa_em_data'):
                    if despesa.parcela_ativa_em_data(data_referencia):
                        despesas_periodo.append(despesa)
                elif hasattr(despesa, 'data_inicio'):
                    if (despesa.data_inicio.year == ano_referencia and 
                        despesa.data_inicio.month == mes_referencia):
                        despesas_periodo.append(despesa)
            
            valor_inquilino = Decimal('0.00')
            valor_credito = Decimal('0.00')
            
            for despesa in despesas_periodo:
                if hasattr(despesa, 'calcular_valor_parcela'):
                    valor_despesa = despesa.calcular_valor_parcela()
                else:
                    valor_despesa = getattr(despesa, 'valor_total', Decimal('0.00'))
                
                if despesa.paga_por == 'inquilino':
                    valor_inquilino += valor_despesa
                elif despesa.paga_por in ['proprietario', 'imobiliaria']:
                    valor_credito += valor_despesa
            
            valor_final = valor_inquilino - valor_credito
            return valor_final
            
        except LookupError:
            return Decimal('0.00')

    @staticmethod
    def get_despesas_periodo_info(contrato, mes_referencia, ano_referencia):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(ano_referencia, mes_referencia, 1)
            
            despesas = Despesa.objects.filter(
                contrato=contrato,
                is_ativa=True
            )
            
            despesas_periodo = []
            for despesa in despesas:
                if hasattr(despesa, 'parcela_ativa_em_data'):
                    if despesa.parcela_ativa_em_data(data_referencia):
                        despesas_periodo.append(despesa)
                elif hasattr(despesa, 'data_inicio'):
                    if (despesa.data_inicio.year == ano_referencia and 
                        despesa.data_inicio.month == mes_referencia):
                        despesas_periodo.append(despesa)
            
            debitos_inquilino = []
            creditos_proprietario = []
            total_debitos = Decimal('0.00')
            total_creditos = Decimal('0.00')
            
            for despesa in despesas_periodo:
                if hasattr(despesa, 'calcular_valor_parcela'):
                    valor = despesa.calcular_valor_parcela()
                else:
                    valor = getattr(despesa, 'valor_total', Decimal('0.00'))
                
                tipo_nome = "Despesa"
                if hasattr(despesa, 'tipo') and despesa.tipo:
                    tipo_nome = getattr(despesa.tipo, 'nome', 'Despesa')
                
                item = {
                    'id': despesa.id,
                    'tipo': tipo_nome,
                    'descricao': getattr(despesa, 'descricao', None) or f"Despesa de {tipo_nome}",
                    'valor': float(valor),
                    'paga_por': despesa.paga_por,
                    'data_inicio': despesa.data_inicio.strftime('%Y-%m-%d') if hasattr(despesa, 'data_inicio') else None
                }
                
                if despesa.paga_por == 'inquilino':
                    debitos_inquilino.append(item)
                    total_debitos += valor
                elif despesa.paga_por in ['proprietario', 'imobiliaria']:
                    creditos_proprietario.append(item)
                    total_creditos += valor
            
            return {
                'debitos_inquilino': debitos_inquilino,
                'creditos_proprietario': creditos_proprietario,
                'total_debitos': float(total_debitos),
                'total_creditos': float(total_creditos),
                'periodo_filtrado': f"{mes_referencia:02d}/{ano_referencia}",
                'despesas_filtradas': len(despesas_periodo),
                'despesas_totais_ativas': despesas.count()
            }
            
        except LookupError:
            return {
                'debitos_inquilino': [],
                'creditos_proprietario': [],
                'total_debitos': 0.0,
                'total_creditos': 0.0,
                'periodo_filtrado': f"{mes_referencia:02d}/{ano_referencia}",
                'despesas_filtradas': 0,
                'despesas_totais_ativas': 0
            }

    # === MÉTODOS PARA CÁLCULO DE REPASSE ===
    
    @staticmethod
    def calcular_valor_repasse_correto(cobranca):
        """
        🎯 NOVO: Calcula repasse usando a lógica correta de incidência de taxa
        
        Este é o método que resolve seu problema!
        """
        print(f"🎯 Calculando repasse correto para cobrança #{cobranca.id}")
        
        # Se já tem composição com incidência nos detalhes, usar
        if (hasattr(cobranca, 'detalhes_calculo') and 
            cobranca.detalhes_calculo and 
            'composicao_com_incidencia' in cobranca.detalhes_calculo):
            
            composicao = cobranca.detalhes_calculo['composicao_com_incidencia']
            valor_repasse = Decimal(str(composicao['valor_liquido_repasse']))
            print(f"   ✅ Usando composição existente: R$ {valor_repasse:.2f}")
            
        else:
            # Calcular nova composição
            composicao = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
                cobranca.contrato,
                cobranca.mes_referencia,
                cobranca.ano_referencia
            )
            valor_repasse = composicao['valor_liquido_repasse']
            print(f"   🧮 Calculado agora: R$ {valor_repasse:.2f}")
        
        return valor_repasse

    # === MÉTODOS ORIGINAIS PARA COMPATIBILIDADE ===
    
    @staticmethod
    def calcular_taxa_administracao(contrato, valor_aluguel):
        """MÉTODO ORIGINAL - mantido sem alteração"""
        if not contrato or not valor_aluguel:
            return Decimal('0.00')
        
        try:
            tipo_taxa = getattr(contrato, 'tipo_taxa', None)
            
            if tipo_taxa == 'percentual':
                percentual = getattr(contrato, 'valor_taxa_administracao_percentual', Decimal('0.00'))
                if percentual:
                    return (Decimal(str(valor_aluguel)) * percentual / Decimal('100')).quantize(Decimal('0.01'))
            
            elif tipo_taxa == 'fixo':
                valor_fixo = getattr(contrato, 'valor_taxa_administracao_fixo', Decimal('0.00'))
                return Decimal(str(valor_fixo or 0))
            
        except (AttributeError, TypeError):
            pass
        
        return Decimal('0.00')

    @staticmethod
    def calcular_valor_repasse(cobranca):
        """MÉTODO ORIGINAL - mantido mas com aviso de que existe versão melhor"""
        print("⚠️ AVISO: Usando método de repasse antigo. Use calcular_valor_repasse_correto() para lógica atualizada.")
        
        if not cobranca:
            return Decimal('0.00')
        
        valor_total = cobranca.valor_total if hasattr(cobranca, 'valor_total') else cobranca.valor
        taxa_administracao = getattr(cobranca, 'calcular_valor_administracao', lambda: Decimal('0.00'))()
        
        try:
            Despesa = apps.get_model('financeiro', 'Despesa')
            data_referencia = datetime.date(cobranca.ano_referencia, cobranca.mes_referencia, 1)
            
            despesas_proprietario = Despesa.objects.filter(
                contrato=cobranca.contrato,
                is_ativa=True,
                paga_por='proprietario'
            )
            
            valor_despesas_proprietario = Decimal('0.00')
            for d in despesas_proprietario:
                if hasattr(d, 'parcela_ativa_em_data') and d.parcela_ativa_em_data(data_referencia):
                    if hasattr(d, 'calcular_valor_parcela'):
                        valor_despesas_proprietario += d.calcular_valor_parcela()
                    else:
                        valor_despesas_proprietario += getattr(d, 'valor_total', Decimal('0.00'))
            
        except LookupError:
            valor_despesas_proprietario = Decimal('0.00')
        
        valor_repasse = valor_total - taxa_administracao - valor_despesas_proprietario
        return max(valor_repasse, Decimal('0.00'))


# === FUNÇÕES UTILITÁRIAS ===

def atualizar_cobrancas_julho_2025():
    """
    🔧 Função para atualizar as cobranças de 07/2025 com a nova lógica
    
    Execute esta função para corrigir as cobranças já criadas
    """
    from financeiro.models import Cobranca
    
    print("🔧 Atualizando cobranças de Julho/2025 com nova lógica de incidência...")
    
    # Buscar cobranças de julho/2025
    cobrancas_julho = Cobranca.objects.filter(
        mes_referencia=7,
        ano_referencia=2025
    )
    
    print(f"📋 Encontradas {cobrancas_julho.count()} cobranças de 07/2025")
    
    total_atualizadas = 0
    total_erros = 0
    
    for cobranca in cobrancas_julho:
        try:
            print(f"\n🔄 Processando cobrança #{cobranca.id} - {cobranca.contrato}")
            
            # Recalcular com nova lógica
            composicao = CobrancaCalculadoraService.recalcular_detalhes_cobranca(cobranca)
            
            # Mostrar resultado
            print(f"   💰 Valor total: R$ {composicao['valor_total_cobranca']:.2f}")
            print(f"   🏛️ Taxa admin: R$ {composicao['valor_taxa_administrativa']:.2f}")
            print(f"   🎯 Repasse: R$ {composicao['valor_liquido_repasse']:.2f}")
            
            total_atualizadas += 1
            
        except Exception as e:
            print(f"   ❌ Erro na cobrança #{cobranca.id}: {e}")
            total_erros += 1
    
    print(f"\n✅ RESULTADO:")
    print(f"   - Atualizadas: {total_atualizadas}")
    print(f"   - Erros: {total_erros}")
    print(f"   - Total: {cobrancas_julho.count()}")


def debug_cobranca_especifica(cobranca_id):
    """
    🐛 Debug detalhado de uma cobrança específica
    """
    from financeiro.models import Cobranca
    
    try:
        cobranca = Cobranca.objects.get(id=cobranca_id)
        
        print(f"🐛 DEBUG: Cobrança #{cobranca_id}")
        print("=" * 50)
        print(f"Contrato: {cobranca.contrato}")
        print(f"Período: {cobranca.mes_referencia:02d}/{cobranca.ano_referencia}")
        print(f"Valor atual: R$ {cobranca.valor:.2f}")
        print(f"Status: {cobranca.status}")
        
        print(f"\n🧮 RECALCULO COM NOVA LÓGICA:")
        composicao = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
            cobranca.contrato,
            cobranca.mes_referencia,
            cobranca.ano_referencia
        )
        
        print(f"\n📊 RESULTADO:")
        for componente in composicao['componentes']:
            print(f"• {componente['descricao']}: R$ {componente['valor']:.2f}")
            if componente['tem_incidencia_taxa']:
                print(f"  - Taxa: R$ {componente['valor_taxa_admin']:.2f}")
                print(f"  - Líquido: R$ {componente['valor_liquido']:.2f}")
            else:
                print(f"  - Sem taxa administrativa")
        
        print(f"\n🎯 RESUMO:")
        print(f"Total cobrança: R$ {composicao['valor_total_cobranca']:.2f}")
        print(f"Base taxa ({composicao['taxa_admin_percentual']}%): R$ {composicao['valor_com_incidencia']:.2f}")
        print(f"Isento taxa: R$ {composicao['valor_sem_incidencia']:.2f}")
        print(f"Taxa admin: R$ {composicao['valor_taxa_administrativa']:.2f}")
        print(f"REPASSE LÍQUIDO: R$ {composicao['valor_liquido_repasse']:.2f}")
        
        return composicao
        
    except Cobranca.DoesNotExist:
        print(f"❌ Cobrança #{cobranca_id} não encontrada")
        return None


def comparar_calculo_antigo_vs_novo(cobranca_id):
    """
    ⚖️ Compara cálculo antigo vs novo para uma cobrança
    """
    from financeiro.models import Cobranca
    
    try:
        cobranca = Cobranca.objects.get(id=cobranca_id)
        
        print(f"⚖️ COMPARAÇÃO: Cobrança #{cobranca_id}")
        print("=" * 60)
        
        # CÁLCULO ANTIGO
        print(f"🕰️ MÉTODO ANTIGO:")
        valor_total_antigo = cobranca.valor
        
        # Simular taxa sobre valor total (método incorreto)
        taxa_admin_percentual = CobrancaCalculadoraService._obter_taxa_admin_contrato(cobranca.contrato)
        taxa_admin_antiga = valor_total_antigo * (taxa_admin_percentual / 100)
        repasse_antigo = valor_total_antigo - taxa_admin_antiga
        
        print(f"   Total cobrança: R$ {valor_total_antigo:.2f}")
        print(f"   Taxa admin ({taxa_admin_percentual}%): R$ {taxa_admin_antiga:.2f}")
        print(f"   Repasse: R$ {repasse_antigo:.2f}")
        
        # CÁLCULO NOVO
        print(f"\n🆕 MÉTODO NOVO:")
        composicao = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
            cobranca.contrato,
            cobranca.mes_referencia,
            cobranca.ano_referencia
        )
        
        print(f"   Total cobrança: R$ {composicao['valor_total_cobranca']:.2f}")
        print(f"   Base taxa: R$ {composicao['valor_com_incidencia']:.2f}")
        print(f"   Isento taxa: R$ {composicao['valor_sem_incidencia']:.2f}")
        print(f"   Taxa admin ({composicao['taxa_admin_percentual']}%): R$ {composicao['valor_taxa_administrativa']:.2f}")
        print(f"   Repasse: R$ {composicao['valor_liquido_repasse']:.2f}")
        
        # DIFERENÇA
        print(f"\n📊 DIFERENÇA:")
        diff_taxa = composicao['valor_taxa_administrativa'] - taxa_admin_antiga
        diff_repasse = composicao['valor_liquido_repasse'] - repasse_antigo
        
        print(f"   Taxa admin: {'+' if diff_taxa >= 0 else ''}R$ {diff_taxa:.2f}")
        print(f"   Repasse: {'+' if diff_repasse >= 0 else ''}R$ {diff_repasse:.2f}")
        
        if abs(diff_repasse) > Decimal('0.01'):
            print(f"   ⚠️ IMPACTO: Diferença significativa no repasse!")
        else:
            print(f"   ✅ Sem impacto significativo")
        
        return {
            'antigo': {
                'taxa_admin': taxa_admin_antiga,
                'repasse': repasse_antigo
            },
            'novo': {
                'taxa_admin': composicao['valor_taxa_administrativa'],
                'repasse': composicao['valor_liquido_repasse']
            },
            'diferenca': {
                'taxa_admin': diff_taxa,
                'repasse': diff_repasse
            }
        }
        
    except Cobranca.DoesNotExist:
        print(f"❌ Cobrança #{cobranca_id} não encontrada")
        return None


def gerar_relatorio_impacto_julho_2025():
    """
    📊 Gera relatório de impacto das mudanças nas cobranças de julho/2025
    """
    from financeiro.models import Cobranca
    
    print("📊 RELATÓRIO DE IMPACTO - JULHO/2025")
    print("=" * 50)
    
    cobrancas_julho = Cobranca.objects.filter(
        mes_referencia=7,
        ano_referencia=2025
    )
    
    total_cobrancas = cobrancas_julho.count()
    total_valor_antigo = Decimal('0.00')
    total_taxa_antiga = Decimal('0.00')
    total_repasse_antigo = Decimal('0.00')
    
    total_valor_novo = Decimal('0.00')
    total_taxa_nova = Decimal('0.00')
    total_repasse_novo = Decimal('0.00')
    
    cobrancas_com_impacto = 0
    maior_diferenca_repasse = Decimal('0.00')
    
    print(f"Analisando {total_cobrancas} cobranças...")
    
    for cobranca in cobrancas_julho:
        try:
            # Simular cálculo antigo
            valor_total = cobranca.valor
            taxa_admin_percentual = CobrancaCalculadoraService._obter_taxa_admin_contrato(cobranca.contrato)
            taxa_antiga = valor_total * (taxa_admin_percentual / 100)
            repasse_antigo = valor_total - taxa_antiga
            
            # Cálculo novo
            composicao = CobrancaCalculadoraService.calcular_composicao_com_incidencia(
                cobranca.contrato,
                cobranca.mes_referencia,
                cobranca.ano_referencia
            )
            
            # Acumular totais
            total_valor_antigo += valor_total
            total_taxa_antiga += taxa_antiga
            total_repasse_antigo += repasse_antigo
            
            total_valor_novo += composicao['valor_total_cobranca']
            total_taxa_nova += composicao['valor_taxa_administrativa']
            total_repasse_novo += composicao['valor_liquido_repasse']
            
            # Verificar impacto
            diff_repasse = composicao['valor_liquido_repasse'] - repasse_antigo
            if abs(diff_repasse) > Decimal('0.01'):
                cobrancas_com_impacto += 1
                if abs(diff_repasse) > abs(maior_diferenca_repasse):
                    maior_diferenca_repasse = diff_repasse
            
        except Exception as e:
            print(f"Erro na cobrança {cobranca.id}: {e}")
    
    # Imprimir resultado
    print(f"\n📈 RESULTADO CONSOLIDADO:")
    print(f"Total de cobranças: {total_cobrancas}")
    print(f"Cobranças com impacto: {cobrancas_com_impacto}")
    
    print(f"\n💰 VALORES TOTAIS:")
    print(f"Valor total cobranças:")
    print(f"  - Antigo: R$ {total_valor_antigo:,.2f}")
    print(f"  - Novo: R$ {total_valor_novo:,.2f}")
    print(f"  - Diferença: R$ {total_valor_novo - total_valor_antigo:,.2f}")
    
    print(f"\nTaxa administrativa:")
    print(f"  - Antigo: R$ {total_taxa_antiga:,.2f}")
    print(f"  - Novo: R$ {total_taxa_nova:,.2f}")
    print(f"  - Diferença: R$ {total_taxa_nova - total_taxa_antiga:,.2f}")
    
    print(f"\nRepasse aos proprietários:")
    print(f"  - Antigo: R$ {total_repasse_antigo:,.2f}")
    print(f"  - Novo: R$ {total_repasse_novo:,.2f}")
    print(f"  - Diferença: R$ {total_repasse_novo - total_repasse_antigo:,.2f}")
    
    print(f"\n🎯 IMPACTO:")
    print(f"Maior diferença individual: R$ {maior_diferenca_repasse:,.2f}")
    print(f"Percentual de cobranças afetadas: {(cobrancas_com_impacto/total_cobrancas*100):.1f}%")

