# --- START OF FILE app/extensions.py ---

# ✅ NUEVO ARCHIVO

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_login import LoginManager

# Creamos las instancias de las extensiones aquí
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
login_manager = LoginManager()