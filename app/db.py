# --- START OF FILE app/db.py ---

import sqlite3
import unicodedata

DB_FILE = "noticias.db" # Esta variable ya no se usa, pero la dejamos por si acaso

# ✅ CAMBIO: Esta función ya no es necesaria para PostgreSQL
# def normalize_text(text: str) -> str:
#     if not text: return ""
#     nfkd_form = unicodedata.normalize('NFD', text.lower())
#     return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def get_db_connection():
    # Esta función ahora es OBSOLETA y será eliminada en el futuro.
    # La mantenemos temporalmente para que las rutas no refactorizadas no fallen.
    conn = sqlite3.connect("noticias.db")
    conn.row_factory = sqlite3.Row
    # conn.create_function("normalize", 1, normalize_text) # <-- Eliminamos esta línea
    return conn