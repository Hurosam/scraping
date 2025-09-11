# --- START OF FILE app/util/helpers.py ---

# ✅ NUEVO ARCHIVO

from datetime import datetime

def format_relative_time(date_str: str) -> str:
    """
    Convierte una fecha ISO a un formato de tiempo relativo (ej: "hace 2 días").
    """
    if not date_str:
        return "Fecha no disponible"
    try:
        # Tomamos solo la parte de la fecha para evitar problemas con la zona horaria
        date_obj = datetime.fromisoformat(date_str.split('T')[0])
        now = datetime.now()
        diff = now - date_obj

        if diff.days > 7:
            return date_obj.strftime('%d/%m/%Y')
        if diff.days > 0:
            return f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
        if diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"hace {hours} hora{'s' if hours > 1 else ''}"
        if diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
        
        return "Hace un momento"
    except (ValueError, TypeError):
        return date_str

def format_absolute_date(date_str: str) -> str:
    """
    Convierte una fecha ISO a un formato de fecha absoluto (DD/MM/YYYY).
    """
    if not date_str:
        return "Fecha no disponible"
    try:
        date_obj = datetime.fromisoformat(date_str.split('T')[0])
        return date_obj.strftime('%d/%m/%Y')
    except (ValueError, TypeError):
        return date_str