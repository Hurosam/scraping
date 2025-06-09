import sqlite3
from flask import Flask, render_template

# Inicializar la aplicación Flask
app = Flask(__name__)

# Nombre del archivo de la base de datos
DB_FILE = "noticias.db"

def get_db_connection():
    """Crea y devuelve una conexión a la base de datos."""
    try:
        conn = sqlite3.connect(DB_FILE)
        # Esto permite acceder a los resultados por nombre de columna
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

@app.route('/')
def index():
    """
    Ruta principal que muestra las noticias.
    """
    conn = get_db_connection()
    if conn is None:
        # Si no se puede conectar a la DB, muestra un mensaje de error
        return (
            "<h1>Error: No se pudo conectar a la base de datos 'noticias.db'.</h1>"
            "<p>Asegúrate de que el archivo existe y de que los scripts de scraping y creación de base de datos se han ejecutado correctamente.</p>"
        )

    # Consultamos la tabla 'articulos_detallados' porque tiene la información más completa.
    # Usamos 'rowid' para ordenar por inserción (los más recientes primero).
    try:
        articles_cursor = conn.execute(
            "SELECT scraped_article_title, link, first_paragraph "
            "FROM articulos_detallados "
            "ORDER BY rowid DESC"
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        # Este error ocurre si la tabla no existe
        conn.close()
        return (
            "<h1>Error: La tabla 'articulos_detallados' no se encontró en la base de datos.</h1>"
            "<p>Por favor, ejecuta <code>python create_database.py</code> para crearla.</p>"
        )

    # Convertimos los resultados del cursor a una lista de diccionarios
    all_articles = [dict(row) for row in articles_cursor]

    # Separamos la noticia más reciente (la primera de la lista) del resto
    hero_article = None
    other_articles = []

    if all_articles:
        hero_article = all_articles[0]
        other_articles = all_articles[1:]

    # Pasamos los datos a la plantilla HTML para que los muestre
    return render_template('index.html', hero=hero_article, articles=other_articles)

# El script comienza a ejecutarse aquí
if __name__ == '__main__':
    # Ejecuta la aplicación en modo de depuración para facilitar el desarrollo
    print("Iniciando el servidor web...")
    print("Abre tu navegador y visita: http://127.0.0.1:5000")
    app.run(debug=True)