from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from functools import wraps
from werkzeug.security import check_password_hash

# Definición del Blueprint para la autenticación. 
# Esto permite manejar todas las rutas de autenticación dentro de un módulo independiente (auth).
auth_bp = Blueprint('auth', __name__)

# Decorador personalizado para verificar si un usuario ha iniciado sesión antes de acceder a ciertas rutas.
# Envuelve las funciones protegidas para redirigir a la página de inicio de sesión si el usuario no está autenticado.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:  # Verifica si la clave 'usuario' existe en la sesión
            flash("Por favor, inicia sesión para acceder a esta página.", "warning")  # Mensaje de advertencia
            return redirect(url_for('auth.login'))  # Redirige a la página de login si no está autenticado
        return f(*args, **kwargs)  # Permite el acceso a la función protegida si el usuario está autenticado
    return decorated_function

# Ruta para iniciar sesión ("/login"), admite métodos GET y POST.
# Muestra el formulario de inicio de sesión (GET) y procesa el inicio de sesión del usuario (POST).
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Recupera los datos del formulario enviados por el usuario
        username = request.form['username']
        password = request.form['password']
        
        # Consulta para encontrar al usuario en la base de datos a partir del nombre de usuario
        usuario = current_app.db.session.query(current_app.Usuario).filter_by(username=username).first()
        
        # Verificación de credenciales: si el usuario existe y la contraseña es correcta
        if usuario and check_password_hash(usuario.password_hash, password):
            # Guarda el nombre de usuario en la sesión para mantener la autenticación
            session['usuario'] = usuario.username
            flash('Sesión iniciada con éxito', 'success')  # Muestra mensaje de éxito
            return redirect(url_for('index'))  # Redirige al usuario a la página principal
        
        # Si las credenciales son incorrectas, muestra un mensaje de error
        flash('Usuario o contraseña incorrectos', 'danger')
    
    # Renderiza el formulario de inicio de sesión en caso de GET o si las credenciales no fueron válidas
    return render_template('login.html')

# Ruta para cerrar sesión ("/logout").
# Elimina al usuario de la sesión y lo redirige a la página de inicio de sesión.
@auth_bp.route('/logout')
def logout():
    session.pop('usuario', None)  # Elimina la clave 'usuario' de la sesión, cerrando la sesión del usuario
    flash('Has cerrado sesión', 'info')  # Muestra un mensaje informando que se ha cerrado sesión
    return redirect(url_for('auth.login'))  # Redirige a la página de inicio de sesión
