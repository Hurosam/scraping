# --- START OF FILE config.py ---

# ✅ NUEVO ARCHIVO

import os

class Config:
    """Configuración base de la aplicación."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-secreta-muy-dificil-de-adivinar'
    
    # Configuración de la base de datos PostgreSQL
    # Reemplaza 'usuario', 'contraseña', 'host' y 'nombre_db' con tus datos.
    # Ejemplo: 'postgresql://postgres:mysecretpassword@localhost/noticias_db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'postgresql://postgres:admin@localhost/noticias_db'
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False