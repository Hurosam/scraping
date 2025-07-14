# --- scrap_tudiario.py ---

import sqlite3
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

URL = "https://tudiariohuanuco.pe/"
DB_FILE = "noticias.db"
SOURCE_NAME = "Tu Diario Huánuco"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def setup_database():
    """Crea la tabla 'articles' con el schema COMPLETO si no existe."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    print("🗄️  Asegurando que la base de datos tenga el schema completo...")

    # Se mantiene el schema completo que ya tenías
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        link TEXT NOT NULL UNIQUE,
        source TEXT,
        status TEXT NOT NULL DEFAULT 'new',
        first_paragraph TEXT,
        full_content TEXT,
        image_url TEXT,
        detected_cities TEXT,
        analysis_summary TEXT,
        analysis_category TEXT,
        analysis_veracity_score INTEGER,
        analysis_veracity_reason TEXT,
        analysis_regional_interest_score INTEGER,
        analysis_regional_interest_reason TEXT,
        analysis_country TEXT,
        analysis_region TEXT,
        analysis_province TEXT,
        analysis_district TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Schema de la base de datos verificado y completo.")

def fetch_page_content(url):
    """Descarga el contenido HTML de una URL dada."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        print(f"🌐 Página {url} obtenida exitosamente.")
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página {url}: {e}")
        return None

# ### NUEVA FUNCIÓN: Extrae los detalles de la página de un artículo.
def scrape_article_details(article_url):
    """
    Visita la página de un artículo y extrae su imagen principal y contenido de texto.
    """
    html_content = fetch_page_content(article_url)
    if not html_content:
        return None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # --- Extracción de la URL de la imagen ---
    image_url = None
    image_tag = soup.select_one('div.entry-thumbnail img')
    if image_tag and image_tag.has_attr('src'):
        image_url = image_tag['src']
        print(f"  -> 🖼️ Imagen encontrada: {image_url[:80]}...")
    else:
        print("  -> ⚠️ No se encontró la imagen principal.")
        
    # --- Extracción del contenido del artículo ---
    content_container = soup.select_one('div.entry-content')
    if not content_container:
        print(f"  -> ⚠️ No se encontró el contenedor de contenido principal.")
        return image_url, None

    # Excluir elementos no deseados como scripts o bloques de anuncios dentro del contenido
    for unwanted in content_container.select('script, style, .afw, .xs_social_share_widget'):
        unwanted.decompose()

    paragraphs = content_container.find_all('p')
    full_text = ' '.join(p.get_text(strip=True) for p in paragraphs)
    
    if len(full_text) < 100: # Asegurarse de que haya contenido sustancial
        print(f"  -> ⚠️ Contenido de texto muy corto encontrado.")
        return image_url, None
         
    print(f"  -> 📄 Texto del artículo extraído correctamente.")
    return image_url, full_text

def parse_and_store_news(html_content):
    """Extrae noticias, obtiene sus detalles y las guarda en la BD."""
    if not html_content:
        print("⚠️ No se recibió contenido HTML de la página principal.")
        return

    soup = BeautifulSoup(html_content, 'html.parser')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    new_articles_added = 0
    
    # Selectores para encontrar los artículos en la página principal
    selectors = [
        'div.tab__post__single--item', 
        'div.hero-content', 
        'div.ts-overlay-style', 
        'div.ts-col-box-item'
    ]
    
    all_links = []
    for selector in selectors:
        for container in soup.select(selector):
            link_tag = container.find('a', href=True)
            if link_tag and link_tag['href'] not in all_links:
                 all_links.append(link_tag['href'])

    print(f"\n🔍 Se encontraron {len(all_links)} enlaces únicos para verificar.")

    for link in all_links:
        # Verificar si el enlace ya existe en la BD para no procesarlo de nuevo.
        cursor.execute("SELECT id FROM articles WHERE link = ?", (link,))
        if cursor.fetchone():
            continue  # La noticia ya existe, pasar a la siguiente.

        # ### CAMBIO: Scrapear detalles para cada noticia nueva.
        print(f"\n✨ Procesando noticia nueva: {link}")
        image_url, full_content = scrape_article_details(link)

        # Solo guardar si tenemos contenido de texto. La imagen es opcional.
        if full_content:
            # Re-extraer el título desde la página del artículo para mayor precisión
            temp_soup = BeautifulSoup(fetch_page_content(link), 'html.parser')
            title_tag = temp_soup.select_one('h1.post-title')
            title = title_tag.get_text(strip=True) if title_tag else "Título no encontrado"

            try:
                # ### CAMBIO: Insertar con el contenido completo, imagen y estado 'processed'.
                cursor.execute(
                    """INSERT INTO articles 
                       (title, link, source, status, full_content, image_url) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (title, link, SOURCE_NAME, 'processed', full_content, image_url)
                )
                conn.commit()
                new_articles_added += 1
                print(f"  -> ✅ Noticia '{title}' guardada en la BD.")
            except sqlite3.IntegrityError:
                print("  -> ℹ️ La noticia ya fue insertada por otro proceso.")
                pass
        else:
            print(f"  -> ❌ No se pudo guardar la noticia por falta de contenido: {link}")
        
        time.sleep(1) # Pequeña pausa para no sobrecargar el servidor

    conn.close()
    print(f"\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias nuevas de '{SOURCE_NAME}'.")

if __name__ == "__main__":
    print(f"\n=== Iniciando scraping de: {SOURCE_NAME} ===")
    setup_database()
    main_html = fetch_page_content(URL)
    if main_html:
        parse_and_store_news(main_html)
    print("\n✅ Scraping completado.")