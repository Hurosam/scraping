# --- START OF FILE app/__init__.py ---

from flask import Flask, render_template
from config import Config
from .extensions import db, migrate, bcrypt, login_manager

def create_app(config_class=Config):
    """
    Función de fábrica para crear y configurar la aplicación Flask.
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # --- 1. Cargar la Configuración ---
    app.config.from_object(config_class)

    # --- 2. Inicializar las Extensiones de Flask ---
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor, inicia sesión para acceder a esta página."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))

    with app.app_context():
        # --- 3. Importar y Registrar Blueprints ---
        from .routes.main_routes import main_bp
        from .routes.api_routes import api_bp
        # ✅ CAMBIO: Importamos y registramos el nuevo Blueprint de autenticación
        from .routes.auth_routes import auth_bp
        
        app.register_blueprint(main_bp)
        app.register_blueprint(api_bp, url_prefix='/api')
        app.register_blueprint(auth_bp) # No necesita prefijo

        # --- 4. Registrar Filtros de Plantilla ---
        from .util.helpers import format_relative_time, format_absolute_date
        app.template_filter('relative_time')(format_relative_time)
        app.template_filter('absolute_date')(format_absolute_date)

        # --- 5. Importar Modelos ---
        from . import models

        # --- 6. Registrar Gestores de Errores Comunes ---
        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('error.html', error_code=404, error_message="La página que buscas no existe."), 404

        @app.errorhandler(500)
        def internal_error(error):
            return render_template('error.html', error_code=500, error_message="Ocurrió un error inesperado en el servidor."), 500

    return app