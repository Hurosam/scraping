# --- START OF FILE app/routes/auth_routes.py ---

# ✅ NUEVO ARCHIVO

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from ..extensions import db
from ..models import User, Role
from ..forms import LoginForm, RegistrationForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Si el usuario ya ha iniciado sesión, redirigirlo a la página principal
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Verificar si el usuario existe y la contraseña es correcta
        if user is None or not user.check_password(form.password.data):
            flash('Correo electrónico o contraseña inválidos.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Si todo es correcto, iniciar sesión con Flask-Login
        login_user(user, remember=form.remember_me.data)
        flash('Has iniciado sesión correctamente.', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('auth/login.html', title='Iniciar Sesión', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        # Crear una nueva instancia de usuario
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        
        # Asignar el rol 'normal' por defecto
        normal_role = Role.query.filter_by(name='normal').first()
        if normal_role:
            user.roles.append(normal_role)
            
        db.session.add(user)
        db.session.commit()
        
        flash('¡Felicidades, tu cuenta ha sido creada! Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/register.html', title='Registro', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Has cerrado la sesión.', 'info')
    return redirect(url_for('main.index'))