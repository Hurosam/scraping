import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuración del script
URL_BASE = "https://diariocorreo.pe"
URL_HUANUCO = f"{URL_BASE}/archivo/edicion/huanuco/"
DB_FILE = "noticias.db"
SOURCE_NAME = "Diario Correo"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...'
}

def setup_database():
    """
    Asegura que la tabla 'articles' exista y tenga TODAS las columnas necesarias.
    """
    print("🗄️ Verificando la estructura de la base de datos...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Crea la tabla principal si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE
        )
    """)

    # 2. Verifica y añade las columnas que puedan faltar
    table_info = cursor.execute("PRAGMA table_info(articles)").fetchall()
    existing_columns = [col[1] for col in table_info]

    required_columns = {
        "source": "TEXT",
        "status": "TEXT NOT NULL DEFAULT 'new'",
        "first_paragraph": "TEXT",
        "full_content": "TEXT",
        "image_url": "TEXT",
        "detected_cities": "TEXT",
        "analysis_summary": "TEXT",
        "analysis_category": "TEXT",
        "analysis_veracity_score": "INTEGER",
        "analysis_veracity_reason": "TEXT",
        "analysis_interest_score": "INTEGER",
        "analysis_interest_reason": "TEXT",
        "analysis_country": "TEXT",
        "analysis_region": "TEXT",
        "analysis_province": "TEXT",
        "analysis_district": "TEXT"
    }

    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            print(f"  -> Añadiendo columna faltante: {col_name}")
            cursor.execute(f"ALTER TABLE articles ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print(" -> Estructura de la base de datos asegurada.")

def fetch_page_content(url):
    """Descarga el contenido HTML de una URL dada."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        print(f"🌐 Página obtenida exitosamente: {url}")
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página {url}: {e}")
        return None

def scrape_article_details(article_url):
    """Extrae contenido e imagen de una noticia específica."""
    html_content = fetch_page_content(article_url)
    if not html_content:
        return None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')

    image_url = None
    og_image_tag = soup.find('meta', property='og:image')
    if og_image_tag:
        image_url = og_image_tag.get('content')

    content_container = soup.select_one('div.story-contents__content')
    if not content_container:
        return None, None, image_url

    paragraphs = content_container.find_all('p', class_='story-contents__font-paragraph')
    full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
    first_paragraph = paragraphs[0].get_text(strip=True) if paragraphs else ""

    if len(full_text) < 50:
        return None, None, image_url

    print(f" -> ✨ Contenido e imagen extraídos de {article_url[:70]}...")
    return first_paragraph, full_text, image_url

def parse_and_store_news(main_page_html):
    """Busca noticias nuevas y las guarda en la base de datos."""
    if not main_page_html:
        print("⚠️ Contenido HTML de la página principal vacío.")
        return

    soup = BeautifulSoup(main_page_html, 'html.parser')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    new_articles_added = 0
    article_containers = soup.select('div.story-item')
    print(f"\n🔍 Buscando noticias en {len(article_containers)} contenedores...")

    if not article_containers:
        print("⚠️ No se encontraron contenedores de noticias.")
        conn.close()
        return

    for container in article_containers:
        title_tag = container.select_one('h2.story-item__content-title a.story-item__title')
        if not title_tag or not title_tag.has_attr('href'):
            continue

        title = title_tag.get_text(strip=True)
        relative_link = title_tag['href']
        full_link = urljoin(URL_BASE, relative_link)

        cursor.execute("SELECT id FROM articles WHERE link = ?", (full_link,))
        if cursor.fetchone():
            continue

        print(f"\n ➕ Noticia nueva encontrada: {title}")
        first_p, full_content, img_url = scrape_article_details(full_link)

        if first_p and full_content:
            try:
                cursor.execute(
                    """
                    INSERT INTO articles (title, link, source, first_paragraph, full_content, image_url, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (title, full_link, SOURCE_NAME, first_p, full_content, img_url, 'processed')
                )
                conn.commit()
                new_articles_added += 1
                print(" -> ✅ Noticia y contenido guardados en la BD.")
            except sqlite3.IntegrityError:
                print(" -> ℹ️ La noticia ya fue insertada.")
        else:
            print(f" -> ❌ No se pudo guardar por falta de contenido: {title}")

    conn.close()
    print(f"\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias de '{SOURCE_NAME}'.")

if __name__ == "__main__":
    print(f"\n=== Iniciando scraping de: {SOURCE_NAME} ===")
    setup_database()
    main_page_html = fetch_page_content(URL_HUANUCO)
    parse_and_store_news(main_page_html)
    print("\n✅ Scraping completado.")
