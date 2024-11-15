import os
from flask import Flask, render_template, get_flashed_messages, flash, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from auth import auth_bp, login_required
from werkzeug.security import generate_password_hash, check_password_hash  # Importación de check_password_hash

# Función para cargar las variables desde el archivo .env
def load_env_file(filepath):
    with open(filepath) as f:
        for line in f:
            # Ignorar líneas en blanco y comentarios
            if line.strip() and not line.startswith("#"):
                # Dividir la línea en clave y valor
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

# Cargar las variables del archivo .env
load_env_file(".env")

# Inicialización de la aplicación Flask
app = Flask(__name__)
# Configuración de la base de datos y clave secreta desde el entorno
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') # Configuración de conexión a la base de datos
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') # Clave secreta para manejar sesiones y otros procesos de seguridad
db = SQLAlchemy(app)  # Inicialización de SQLAlchemy para manejar la base de datos

# Modelo de datos para representar un auto en la base de datos
class Auto(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID único de cada auto
    marca = db.Column(db.String(50), nullable=False)  # Marca del auto (Toyota, Honda, etc.)
    modelo = db.Column(db.String(50), nullable=False)  # Modelo del auto
    ano = db.Column(db.Integer, nullable=False)  # Año de fabricación del auto
    placa = db.Column(db.String(10), unique=True, nullable=False, index=True)  # Placa única del auto (debe tener 6 caracteres)
    precio = db.Column(db.Numeric(10, 2), nullable=False)  # Precio del auto, con 2 decimales

# Modelo de datos para representar un usuario en la base de datos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # ID único de cada usuario
    username = db.Column(db.String(50), unique=True, nullable=False)  # Nombre de usuario único
    password_hash = db.Column(db.String(128), nullable=False)  # Contraseña almacenada como un hash seguro

    # Método para establecer la contraseña de un usuario usando hashing seguro
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

# Agregar `db` y `Usuario` a `current_app` para que estén disponibles en `auth.py`
app.db = db
app.Usuario = Usuario

# Registro del blueprint de autenticación para manejo de login y logout
app.register_blueprint(auth_bp)

# Ruta principal de la aplicación, solo accesible si el usuario ha iniciado sesión
@app.route('/')
@login_required
def index():
    messages = get_flashed_messages(with_categories=True)  # Recupera mensajes flash de otras operaciones
    return render_template('index.html', messages=messages)  # Renderiza la plantilla index.html

# Ruta para ver la lista de autos, con soporte de paginación
@app.route('/ver_autos')
@login_required
def ver_autos():
    page = request.args.get('page', 1, type=int)  # Obtiene el número de página actual (predeterminado 1)
    per_page = request.args.get('per_page', 25, type=int)  # Define la cantidad de autos por página
    autos_paginados = Auto.query.paginate(page=page, per_page=per_page)  # Realiza la paginación
    return render_template('ver_autos.html', autos=autos_paginados, per_page=per_page)  # Renderiza ver_autos.html

# Ruta para filtrar autos según los criterios ingresados por el usuario
@app.route('/filtrar_auto', methods=['GET', 'POST'])
@login_required
def filtrar_auto():
    autos = None
    if request.method == 'POST':
        # Obtiene los valores de los filtros del formulario
        marca = request.form.get('marca')
        ano = request.form.get('ano')
        precio = request.form.get('precio')
        query = Auto.query
        if marca:
            query = query.filter_by(marca=marca)  # Filtra por marca
        if ano:
            query = query.filter_by(ano=int(ano))  # Filtra por año
        if precio:
            query = query.filter(Auto.precio <= float(precio))  # Filtra por precio máximo
        autos = query.all()  # Ejecuta la consulta filtrada
    return render_template('filtrar_auto.html', autos=autos)  # Renderiza filtrar_auto.html con los resultados

# Ruta para agregar un nuevo auto a la base de datos
@app.route('/agregar_auto', methods=['GET', 'POST'])
@login_required
def agregar_auto():
    if request.method == 'POST':
        # Recupera los datos del formulario
        marca = request.form['marca']
        modelo = request.form['modelo']
        ano = int(request.form['ano'])
        placa = request.form['placa']
        precio = float(request.form['precio'])
        
        # Validación de la longitud de la placa
        if len(placa) != 6:
            flash('La placa debe tener exactamente 6 caracteres.', 'danger')  # Mensaje de error si la placa no tiene 6 caracteres
            return render_template('agregar_auto.html', auto_añadido=False)
        
        # Validación para evitar duplicados de placa
        if Auto.query.filter_by(placa=placa).first():
            flash('La placa ingresada ya existe. Intente con otra.', 'danger')  # Mensaje si la placa ya existe
            return render_template('agregar_auto.html', auto_añadido=False)

        # Creación de un nuevo objeto Auto y almacenamiento en la base de datos
        nuevo_auto = Auto(marca=marca, modelo=modelo, ano=ano, placa=placa, precio=precio)
        try:
            db.session.add(nuevo_auto)
            db.session.commit()
            flash('Auto añadido exitosamente', 'success')  # Mensaje de éxito
            return redirect(url_for('index'))  # Redirige a la página principal
        except IntegrityError:
            db.session.rollback()  # Reversa cualquier cambio si ocurre un error de integridad
            flash('Error al añadir el auto. Por favor, intente nuevamente.', 'danger')
    return render_template('agregar_auto.html', auto_añadido=False)  # Renderiza agregar_auto.html

# Ruta para editar los datos de un auto existente
@app.route('/editar_auto/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_auto(id):
    auto = Auto.query.get_or_404(id)  # Obtiene el auto a editar o devuelve un error 404
    if request.method == 'POST':
        # Recupera los datos editados del formulario
        marca = request.form['marca']
        modelo = request.form['modelo']
        ano = int(request.form['ano'])
        placa = request.form['placa']
        precio = float(request.form['precio'])
        
        # Validación para evitar duplicados de placa en otro auto
        auto_existente = Auto.query.filter_by(placa=placa).first()
        if auto_existente and auto_existente.id != id:
            flash('La placa ingresada ya existe en otro auto. Intente con otra.', 'danger')
            return render_template('editar_auto.html', auto=auto, auto_editado=False)

        # Actualización de los atributos del auto
        auto.marca = marca
        auto.modelo = modelo
        auto.ano = ano
        auto.placa = placa
        auto.precio = precio
        db.session.commit()
        flash('Auto actualizado exitosamente', 'success')  # Mensaje de éxito
        return redirect(url_for('index'))
    return render_template('editar_auto.html', auto=auto, auto_editado=False)  # Renderiza editar_auto.html

# Ruta para eliminar un auto de la base de datos, requiere contraseña de supervisor
@app.route('/eliminar_auto/<int:id>', methods=['GET', 'POST'])
@login_required
def eliminar_auto(id):
    auto = Auto.query.get_or_404(id)  # Obtiene el auto a eliminar o devuelve un error 404
    if request.method == 'POST':
        # Verifica la contraseña del supervisor antes de eliminar
        supervisor_password = request.form.get('supervisor_password')
        supervisor = Usuario.query.filter_by(username='supervisor').first()
        
        if supervisor and check_password_hash(supervisor.password_hash, supervisor_password):
            db.session.delete(auto)
            db.session.commit()
            flash('Auto eliminado exitosamente', 'success')  # Mensaje de éxito tras eliminar el auto
            return render_template('eliminar_auto.html', auto_eliminado=True)
        else:
            flash('Contraseña de supervisor incorrecta. Inténtalo de nuevo.', 'danger')
            return redirect(url_for('eliminar_auto', id=id))
    return render_template('eliminar_auto.html', auto=auto, auto_eliminado=False)  # Renderiza eliminar_auto.html

# Inicialización de la base de datos al iniciar la aplicación
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crea las tablas en la base de datos si no existen
    app.run(debug=True)  # Ejecuta la aplicación en modo de depuración
