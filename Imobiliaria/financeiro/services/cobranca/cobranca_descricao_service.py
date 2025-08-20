class CobrancaDescricaoService:
    """Service para geração de descrições automáticas"""
    
    MESES_NOMES = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    @staticmethod
    def gerar_descricao_completa(cobranca):
        """
        Gera descrição completa da cobrança
        """
        if not cobranca:
            return ""
        
        mes_nome = CobrancaDescricaoService.MESES_NOMES.get(
            cobranca.mes_referencia, 
            f'Mês {cobranca.mes_referencia}'
        )
        
        descricao_partes = [
            
            f"Valor do aluguel: {CobrancaDescricaoService._formatar_valor(cobranca.valor_aluguel)}"
        ]
        
        # Adicionar despesas se houver
        despesas = cobranca.get_despesas_cobranca()
        if despesas:
            descricao_partes.append("\nDespesas incluídas:")
            for despesa in despesas:
                nome_despesa = getattr(despesa, 'nome', str(despesa.tipo) if hasattr(despesa, 'tipo') else 'Despesa')
                valor_despesa = despesa.calcular_valor_parcela()
                valor_formatado = CobrancaDescricaoService._formatar_valor(valor_despesa)
                descricao_partes.append(f"• {nome_despesa}: {valor_formatado}")
        
        # Adicionar valor total
        valor_total_formatado = CobrancaDescricaoService._formatar_valor(cobranca.valor_total)
        descricao_partes.append(f"\nValor total: {valor_total_formatado}")
        
        return '\n'.join(descricao_partes)
    
    @staticmethod
    def gerar_descricao_simples(valor_aluguel, mes, ano):
        """
        Gera descrição simples para preview
        """
        mes_nome = CobrancaDescricaoService.MESES_NOMES.get(mes, f'Mês {mes}')
        valor_formatado = CobrancaDescricaoService._formatar_valor(valor_aluguel)
        
        return f"Aluguel referente a {mes_nome} de {ano}\nValor: {valor_formatado}"
    
    @staticmethod
    def gerar_descricao_whatsapp(cobranca):
        """
        Gera descrição formatada para WhatsApp
        """
        if not cobranca or not cobranca.descricao:
            return CobrancaDescricaoService.gerar_descricao_completa(cobranca)
        
        # Limpar e formatar texto existente
        linhas = cobranca.descricao.strip().split('\n')
        linhas_limpas = [linha.strip() for linha in linhas if linha.strip()]
        
        return '\n'.join(linhas_limpas)
    
    @staticmethod
    def _formatar_valor(valor):
        """
        Formata valor monetário para exibição
        """
        if not valor:
            return "R$ 0,00"
        
        # Converter para string formatada
        valor_str = f"{float(valor):,.2f}"
        # Trocar ponto por vírgula (padrão brasileiro)
        valor_str = valor_str.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return f"R$ {valor_str}"