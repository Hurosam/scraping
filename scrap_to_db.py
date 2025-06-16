import sqlite3
import requests
from bs4 import BeautifulSoup

URL = "https://tudiariohuanuco.pe/"
DB_FILE = "noticias.db"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def setup_database():
    """Crea la tabla 'articles' si no existe en la base de datos."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            first_paragraph TEXT,
            detected_cities TEXT,
            analysis_veracity TEXT,
            analysis_country TEXT,
            analysis_region TEXT,
            analysis_province TEXT,
            analysis_district TEXT,
            status TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()
    print("🗄️  Base de datos y tabla 'articles' aseguradas.")

def fetch_page_content(url):
    """Descarga el contenido HTML de la página principal."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        print(f"🌐 Página {url} obtenida exitosamente.")
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página: {e}")
        return None

def parse_and_store_news(html_content):
    """Extrae noticias usando múltiples selectores y las guarda en la BD."""
    if not html_content:
        print("⚠️ Contenido HTML vacío.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    found_articles = {}

    # Lista de selectores CSS para encontrar noticias en distintos formatos
    selectors = [
        'div.tab__post__single--item',
        'div.hero-content',
        'div.ts-overlay-style',
        'div.ts-col-box-item',
        'div.elementor-post__text',
        'div.post-title',  # fallback
    ]

    print("\n🔍 Buscando noticias...")
    for selector in selectors:
        containers = soup.select(selector)
        for container in containers:
            link_tag = container.find('a', href=True)
            if not link_tag:
                continue

            link = link_tag['href']
            title_tag = container.find(['h2', 'h3'])
            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True)

            if title and link and 'tudiariohuanuco.pe' in link and '/categoria/' not in link and len(title) > 10:
                if link not in found_articles:
                    found_articles[link] = title
                    print(f"  ➕ {title}")

    if not found_articles:
        print("⚠️ No se encontraron noticias. ¿La estructura del sitio ha cambiado?")
        return

    print(f"\n✅ Se encontraron {len(found_articles)} noticias únicas.")

    # Guardar en base de datos
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    new_articles_added = 0

    for link, title in found_articles.items():
        try:
            cursor.execute("INSERT INTO articles (title, link) VALUES (?, ?)", (title, link))
            new_articles_added += 1
        except sqlite3.IntegrityError:
            pass  # Noticia ya existe

    conn.commit()
    conn.close()
    print(f"💾 Se añadieron {new_articles_added} noticias nuevas a la base de datos.")

if __name__ == "__main__":
    print("\n=== Paso 1: Scraping de titulares (Multi-Estrategia) ===")
    setup_database()
    html = fetch_page_content(URL)
    parse_and_store_news(html)
    print("✅ Scraping completado.")
