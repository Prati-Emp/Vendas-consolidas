"""
Utilitários de formatação para o dashboard de vendas consolidadas.
Formatação de valores monetários, números e percentuais.
"""

def format_currency(value):
    """
    Formata valor monetário para formato brasileiro com MI (milhões) ou MIL (milhares).
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        String formatada (ex: "R$ 1.5Mi", "R$ 250.0Mil", "R$ 500.0")
    """
    try:
        if value >= 1_000_000:  # Se for 1 milhão ou mais
            return f"R$ {value/1_000_000:.1f}Mi"
        elif value >= 1_000:  # Se for 1 mil ou mais
            return f"R$ {value/1_000:.1f}Mil"
        else:
            return f"R$ {value:.1f}"
    except (TypeError, ValueError):
        return f"R$ {value}"

def format_brl(value):
    """
    Formata valor monetário para Real brasileiro padrão.
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        String formatada (ex: "R$ 1.500.000,00")
    """
    try:
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return f"R$ {value}"

def format_int(value):
    """
    Formata número inteiro com separadores de milhares.
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        String formatada (ex: "1.500")
    """
    try:
        return f"{int(value):,}".replace(',', '.')
    except (TypeError, ValueError):
        return str(value)

def format_percent(value, decimals=1):
    """
    Formata percentual.
    
    Args:
        value: Valor numérico (0-100 ou 0-1)
        decimals: Número de casas decimais
        
    Returns:
        String formatada (ex: "85.5%")
    """
    try:
        # Se o valor está entre 0 e 1, multiplica por 100
        if 0 <= value <= 1:
            value = value * 100
        return f"{value:.{decimals}f}%"
    except (TypeError, ValueError):
        return f"{value}%"

def format_compact_currency(value):
    """
    Formata valor monetário de forma compacta para KPIs.
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        String formatada compacta
    """
    try:
        if value >= 1_000_000_000:  # Bilhões
            return f"R$ {value/1_000_000_000:.1f}Bi"
        elif value >= 1_000_000:  # Milhões
            return f"R$ {value/1_000_000:.1f}Mi"
        elif value >= 1_000:  # Milhares
            return f"R$ {value/1_000:.1f}Mil"
        else:
            return f"R$ {value:.0f}"
    except (TypeError, ValueError):
        return f"R$ {value}"

def format_kpi_value(value, format_type="currency"):
    """
    Formata valor para exibição em KPIs.
    
    Args:
        value: Valor a ser formatado
        format_type: Tipo de formatação ("currency", "number", "percent")
        
    Returns:
        String formatada
    """
    if format_type == "currency":
        return format_compact_currency(value)
    elif format_type == "number":
        return format_int(value)
    elif format_type == "percent":
        return format_percent(value)
    else:
        return str(value)

def normalizar_nome_empreendimento(nome):
    """
    Remove prefixos comuns e normaliza o nome do empreendimento.
    
    Args:
        nome: Nome do empreendimento
        
    Returns:
        Nome normalizado
    """
    if not nome:
        return nome
    
    prefixos = ['Residencial ', 'Loteamento ', 'Condomínio ']
    nome_normalizado = nome
    
    for prefixo in prefixos:
        if nome.startswith(prefixo):
            nome_normalizado = nome.replace(prefixo, '')
            break
    
    return nome_normalizado

def format_delta(value, reference_value):
    """
    Formata variação entre dois valores.
    
    Args:
        value: Valor atual
        reference_value: Valor de referência
        
    Returns:
        String formatada com sinal (ex: "+15.5%", "-2.3%")
    """
    try:
        if reference_value == 0:
            return "N/A"
        
        delta = ((value - reference_value) / reference_value) * 100
        sign = "+" if delta >= 0 else ""
        return f"{sign}{delta:.1f}%"
    except (TypeError, ValueError, ZeroDivisionError):
        return "N/A"

