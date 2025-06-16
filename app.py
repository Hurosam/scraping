import sqlite3
from flask import Flask, render_template

app = Flask(__name__)
DB_FILE = "noticias.db"

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"❌ Error de conexión: {e}")
        return None

@app.route('/')
def index():
    conn = get_db_connection()
    if conn is None:
        return "<h1>Error: No se pudo conectar a la base de datos.</h1>"

    try:
        articles_cursor = conn.execute(
            "SELECT * FROM articles WHERE status = 'analyzed' ORDER BY id DESC"
        ).fetchall()
        conn.close()
    except sqlite3.OperationalError:
        conn.close()
        return "<h1>Error: La tabla 'articles' no existe.</h1><p>Ejecuta `python scrap_to_db.py`.</p>"

    all_articles = [dict(row) for row in articles_cursor]
    hero_article = all_articles[0] if all_articles else None
    other_articles = all_articles[1:] if all_articles else []

    return render_template('index.html', hero=hero_article, articles=other_articles)

if __name__ == '__main__':
    print("🚀 Servidor iniciado en http://127.0.0.1:5000")
    app.run(debug=True)
