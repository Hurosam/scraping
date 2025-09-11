# --- START OF FILE app/forms.py ---

# ✅ NUEVO ARCHIVO

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from .models import User

class LoginForm(FlaskForm):
    """
    Formulario para el inicio de sesión de usuarios.
    Define los campos que se mostrarán en la plantilla login.html.
    """
    email = StringField('Correo Electrónico', validators=[DataRequired(message="El correo es obligatorio."), Email(message="Correo electrónico inválido.")])
    password = PasswordField('Contraseña', validators=[DataRequired(message="La contraseña es obligatoria.")])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    """
    Formulario para el registro de nuevos usuarios.
    Define los campos para la plantilla register.html.
    """
    email = StringField('Correo Electrónico', validators=[DataRequired(message="El correo es obligatorio."), Email(message="Correo electrónico inválido.")])
    password = PasswordField('Contraseña', validators=[DataRequired(message="La contraseña es obligatoria.")])
    password2 = PasswordField(
        'Repetir Contraseña', 
        validators=[DataRequired(message="Por favor, repite la contraseña."), EqualTo('password', message='Las contraseñas deben coincidir.')]
    )
    submit = SubmitField('Registrarse')

    def validate_email(self, email):
        """
        Validador personalizado. WTForms lo llama automáticamente.
        Comprueba en la base de datos si el email ya existe.
        """
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este correo electrónico ya está registrado. Por favor, utiliza otro.')