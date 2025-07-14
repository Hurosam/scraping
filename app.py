import sqlite3
from flask import Flask, render_template, request

app = Flask(__name__)
DB_FILE = "noticias.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    search_query = request.args.get('query', '')
    category_filter = request.args.get('category', '')
    region_filter = request.args.get('region', '')

    conn = get_db_connection()

    # Obtener categorías y regiones disponibles (si ya están en la BD)
    try:
        categories = [row['analysis_category'] for row in conn.execute(
            "SELECT DISTINCT analysis_category FROM articles WHERE analysis_category IS NOT NULL AND status = 'analyzed'"
        )]

        regions = [row['analysis_region'] for row in conn.execute(
            "SELECT DISTINCT analysis_region FROM articles WHERE analysis_region IS NOT NULL AND status = 'analyzed'"
        )]
    except sqlite3.OperationalError:
        categories, regions = [], []

    try:
        sql_query = "SELECT * FROM articles WHERE status = 'analyzed'"
        params = []

        if search_query:
            sql_query += " AND (title LIKE ? OR analysis_summary LIKE ?)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if category_filter:
            sql_query += " AND analysis_category = ?"
            params.append(category_filter)

        if region_filter:
            sql_query += " AND analysis_region LIKE ?"
            params.append(f"%{region_filter}%")

        sql_query += " ORDER BY id DESC"

        articles = [dict(row) for row in conn.execute(sql_query, params).fetchall()]
        conn.close()
    except sqlite3.OperationalError as e:
        conn.close()
        return f"<h1>Error de base de datos: {e}</h1>"

    # Separar la noticia principal del resto
    hero_article = articles[0] if articles else None
    other_articles = articles[1:] if len(articles) > 1 else []

    return render_template(
        'index.html',
        hero=hero_article,
        articles=other_articles,
        query=search_query,
        category_filter=category_filter,
        region_filter=region_filter,
        available_categories=categories,
        available_regions=regions
    )

@app.route('/noticia/<int:article_id>')
def noticia_detalle(article_id):
    conn = get_db_connection()
    article = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    if article is None:
        return "<h1>Artículo no encontrado</h1>", 404
    return render_template('detalle_noticia.html', article=dict(article))

if __name__ == "__main__":
    app.run(debug=True)
