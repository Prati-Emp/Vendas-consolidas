"""
Utilitários de formatação para o app Streamlit de vendas.
Formatação em português brasileiro (pt-BR).
"""

import locale
from typing import Union, Optional

# Configurar locale para pt-BR
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil.1252')
    except locale.Error:
        # Fallback para locale padrão se pt-BR não estiver disponível
        pass

def fmt_brl(valor: Union[float, int], include_symbol: bool = True) -> str:
    """
    Formata valor monetário em reais brasileiros.
    
    Args:
        valor: Valor numérico para formatar
        include_symbol: Se deve incluir o símbolo R$
        
    Returns:
        String formatada (ex: "R$ 1.234,56" ou "1.234,56")
    """
    if valor is None or valor == 0:
        return "R$ 0,00" if include_symbol else "0,00"
    
    try:
        # Usar locale para formatação
        formatted = locale.format_string("%.2f", valor, grouping=True)
        
        if include_symbol:
            return f"R$ {formatted}"
        else:
            return formatted
    except (ValueError, TypeError):
        # Fallback para formatação manual
        valor_str = f"{valor:,.2f}"
        valor_str = valor_str.replace(",", "X").replace(".", ",").replace("X", ".")
        
        if include_symbol:
            return f"R$ {valor_str}"
        else:
            return valor_str

def fmt_int(numero: Union[int, float]) -> str:
    """
    Formata número inteiro com separadores de milhares.
    
    Args:
        numero: Número para formatar
        
    Returns:
        String formatada (ex: "1.234")
    """
    if numero is None:
        return "0"
    
    try:
        return locale.format_string("%d", int(numero), grouping=True)
    except (ValueError, TypeError):
        # Fallback para formatação manual
        return f"{int(numero):,}".replace(",", ".")

def fmt_percent(valor: float, decimals: int = 1) -> str:
    """
    Formata valor como percentual.
    
    Args:
        valor: Valor decimal (ex: 0.15 para 15%)
        decimals: Número de casas decimais
        
    Returns:
        String formatada (ex: "15,0%")
    """
    if valor is None:
        return "0,0%"
    
    try:
        percent_value = valor * 100
        formatted = locale.format_string(f"%.{decimals}f", percent_value, grouping=True)
        return f"{formatted}%"
    except (ValueError, TypeError):
        # Fallback para formatação manual
        percent_value = valor * 100
        formatted = f"{percent_value:.{decimals}f}"
        formatted = formatted.replace(".", ",")
        return f"{formatted}%"

def fmt_date(data, format_str: str = "%d/%m/%Y") -> str:
    """
    Formata data em formato brasileiro.
    
    Args:
        data: Data para formatar (datetime, date ou string)
        format_str: Formato de saída
        
    Returns:
        String formatada (ex: "15/03/2025")
    """
    if data is None:
        return "—"
    
    try:
        if hasattr(data, 'strftime'):
            return data.strftime(format_str)
        else:
            # Tentar converter string para datetime
            from datetime import datetime
            if isinstance(data, str):
                # Tentar diferentes formatos de entrada
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        dt = datetime.strptime(data, fmt)
                        return dt.strftime(format_str)
                    except ValueError:
                        continue
            return str(data)
    except (ValueError, TypeError):
        return str(data) if data else "—"

def fmt_number(valor: Union[float, int], decimals: int = 2) -> str:
    """
    Formata número com separadores de milhares e casas decimais.
    
    Args:
        valor: Número para formatar
        decimals: Número de casas decimais
        
    Returns:
        String formatada (ex: "1.234,56")
    """
    if valor is None:
        return "0,00"
    
    try:
        return locale.format_string(f"%.{decimals}f", valor, grouping=True)
    except (ValueError, TypeError):
        # Fallback para formatação manual
        formatted = f"{valor:,.{decimals}f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted

def fmt_compact_number(valor: Union[float, int]) -> str:
    """
    Formata número em formato compacto (K, M, B).
    
    Args:
        valor: Número para formatar
        
    Returns:
        String formatada (ex: "1,2M", "500K")
    """
    if valor is None or valor == 0:
        return "0"
    
    abs_valor = abs(valor)
    
    if abs_valor >= 1_000_000_000:
        return f"{valor / 1_000_000_000:.1f}B".replace(".", ",")
    elif abs_valor >= 1_000_000:
        return f"{valor / 1_000_000:.1f}M".replace(".", ",")
    elif abs_valor >= 1_000:
        return f"{valor / 1_000:.1f}K".replace(".", ",")
    else:
        return fmt_int(valor)

def fmt_compact_currency(valor: Union[float, int]) -> str:
    """
    Formata valor monetário em formato compacto.
    
    Args:
        valor: Valor para formatar
        
    Returns:
        String formatada (ex: "R$ 1,2M", "R$ 500K")
    """
    if valor is None or valor == 0:
        return "R$ 0"
    
    compact = fmt_compact_number(valor)
    return f"R$ {compact}"

def format_ag_grid_currency(value: float) -> str:
    """
    Formata valor para AG Grid com formatação de moeda.
    
    Args:
        value: Valor para formatar
        
    Returns:
        String formatada para AG Grid
    """
    if value is None or value == 0:
        return "R$ 0,00"
    
    try:
        # Formatação específica para AG Grid
        formatted = locale.format_string("%.2f", value, grouping=True)
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        # Fallback
        formatted = f"{value:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"

def format_ag_grid_number(value: Union[float, int]) -> str:
    """
    Formata número para AG Grid.
    
    Args:
        value: Número para formatar
        
    Returns:
        String formatada para AG Grid
    """
    if value is None:
        return "0"
    
    try:
        return locale.format_string("%.0f", value, grouping=True)
    except (ValueError, TypeError):
        return f"{int(value):,}".replace(",", ".")

def format_ag_grid_decimal(value: float, decimals: int = 2) -> str:
    """
    Formata número decimal para AG Grid.
    
    Args:
        value: Número para formatar
        decimals: Número de casas decimais
        
    Returns:
        String formatada para AG Grid
    """
    if value is None:
        return "0,00"
    
    try:
        return locale.format_string(f"%.{decimals}f", value, grouping=True)
    except (ValueError, TypeError):
        formatted = f"{value:,.{decimals}f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted

# Funções de formatação específicas para KPIs
def format_kpi_value(valor: Union[float, int], tipo: str = "currency") -> str:
    """
    Formata valores para KPIs com diferentes tipos.
    
    Args:
        valor: Valor para formatar
        tipo: Tipo de formatação ("currency", "number", "percent")
        
    Returns:
        String formatada
    """
    if valor is None:
        return "0"
    
    if tipo == "currency":
        return fmt_brl(valor)
    elif tipo == "number":
        return fmt_int(valor)
    elif tipo == "percent":
        return fmt_percent(valor)
    else:
        return str(valor)

def format_tooltip_value(valor: Union[float, int], tipo: str = "currency") -> str:
    """
    Formata valores para tooltips com formatação completa.
    
    Args:
        valor: Valor para formatar
        tipo: Tipo de formatação
        
    Returns:
        String formatada para tooltip
    """
    if valor is None:
        return "N/A"
    
    if tipo == "currency":
        return fmt_brl(valor, include_symbol=True)
    elif tipo == "number":
        return fmt_int(valor)
    elif tipo == "percent":
        return fmt_percent(valor, decimals=2)
    else:
        return str(valor)

# Funções para formatação de dados nulos/vazios
def handle_null_value(valor: Optional[str], default: str = "—") -> str:
    """
    Trata valores nulos ou vazios.
    
    Args:
        valor: Valor para verificar
        default: Valor padrão para nulos
        
    Returns:
        Valor tratado
    """
    if valor is None or valor == "" or str(valor).strip() == "":
        return default
    return str(valor).strip()

def format_drilldown_value(valor: Union[float, int, str], tipo: str = "text") -> str:
    """
    Formata valores para tabela drill-down.
    
    Args:
        valor: Valor para formatar
        tipo: Tipo de formatação
        
    Returns:
        String formatada
    """
    if valor is None:
        return "—"
    
    if tipo == "currency":
        return fmt_brl(valor)
    elif tipo == "number":
        return fmt_int(valor)
    elif tipo == "decimal":
        return fmt_number(valor)
    else:
        return handle_null_value(str(valor))

