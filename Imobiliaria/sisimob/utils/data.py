from datetime import date
import numpy as np

def dia_util_anterior(data: date, dias_uteis: int = 0) -> date:
    """
    Retorna a data ajustada para dias úteis anteriores a uma data alvo.
    Se dias_uteis = 0, retorna a própria data ou o último dia útil anterior.
    """
    return np.busday_offset(data, -dias_uteis, roll='forward').astype(date)
