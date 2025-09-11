# --- START OF FILE run.py ---

from app import create_app
from app.extensions import db
# ✅ CAMBIO: Importamos los modelos User y Role para poder usarlos en los comandos
from app.models import User, Role

app = create_app()

@app.cli.command("seed")
def seed():
    """Inserta los roles iniciales en la base de datos."""
    print("Sembrando roles iniciales...")
    initial_roles = ['admin', 'suscrito', 'noticiero', 'normal']
    for role_name in initial_roles:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            new_role = Role(name=role_name)
            db.session.add(new_role)
            print(f"  - Rol '{role_name}' creado.")
    
    db.session.commit()
    print("✅ Roles sembrados con éxito.")


@app.cli.command("create-admin")
def create_admin():
    """Crea el usuario administrador inicial."""
    # ✅ CAMBIO: Envolvemos el código en un app_context para asegurar el acceso a la BD
    with app.app_context():
        email = input("Introduce el email del administrador: ")
        password = input("Introduce la contraseña: ")
        
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"Error: Ya existe un usuario con el email '{email}'.")
            return
            
        new_admin = User(email=email)
        new_admin.set_password(password)
        
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            print("Error: El rol 'admin' no existe. Ejecuta 'flask seed' primero.")
            return
            
        # Asignamos el rol de admin y también el de normal
        normal_role = Role.query.filter_by(name='normal').first()
        new_admin.roles.append(admin_role)
        if normal_role:
            new_admin.roles.append(normal_role)
        
        db.session.add(new_admin)
        db.session.commit()
        print(f"✅ Administrador '{email}' creado con éxito.")


if __name__ == '__main__':
    app.run(debug=True)