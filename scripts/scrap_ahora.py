# --- START OF FILE scripts/scrap_ahora.py ---

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
from dateutil.parser import isoparse, ParserError

from app import create_app
from app.extensions import db
from app.models import Article, NewsSource

app = create_app()

# --- Constantes del Scraper ---
URL_BASE = "https://ahora.com.pe"
SOURCE_NAME_KEY = "diario_ahora"
SOURCE_DISPLAY_NAME = "Diario Ahora"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def get_or_create_source(session):
    """Busca la fuente de noticias en la BD. Si no existe, la crea."""
    source = session.query(NewsSource).filter_by(name=SOURCE_NAME_KEY).first()
    if not source:
        print(f"Fuente '{SOURCE_DISPLAY_NAME}' no encontrada, creándola...")
        source = NewsSource(name=SOURCE_NAME_KEY, display_name=SOURCE_DISPLAY_NAME)
        session.add(source)
        session.commit()
    return source

def fetch_page_content(url):
    """Obtiene el contenido HTML de una URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página {url}: {e}")
        return None

def scrape_article_details(article_url):
    """Extrae los detalles de una página de artículo de Diario Ahora."""
    html_content = fetch_page_content(article_url)
    if not html_content:
        return None, None, None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    title = (soup.select_one('h1.entry-title, h1.brxe-post-title').get_text(strip=True) 
             if soup.select_one('h1.entry-title, h1.brxe-post-title') else "Título no encontrado")

    first_paragraph, full_content = None, None
    content_container = soup.select_one('div.entry-content, div.brxe-post-content')
    if content_container:
        paragraphs = [p.get_text(strip=True) for p in content_container.find_all('p') if p.get_text(strip=True)]
        if paragraphs:
            first_paragraph = paragraphs[0]
            full_content = '\n'.join(paragraphs)

    image_url = None
    main_image_tag = soup.select_one('.post-thumbnail img, .featured-image img, .entry-content img')
    if main_image_tag and main_image_tag.has_attr('src'):
        width = int(main_image_tag.get('width', 151))
        height = int(main_image_tag.get('height', 151))
        if width > 150 and height > 150:
            image_url = main_image_tag['src']

    if not image_url:
        og_image_tag = soup.find('meta', property='og:image')
        if og_image_tag and og_image_tag.get('content'):
            potential_url = og_image_tag['content']
            if not any(keyword in potential_url for keyword in ['logo', 'cropped', 'avatar', 'default']):
                image_url = potential_url

    published_date_str = None
    meta_date_tag = soup.find('meta', property='article:published_time')
    if meta_date_tag and meta_date_tag.get('content'):
        published_date_str = meta_date_tag['content']
    
    if not published_date_str:
        published_date_str = datetime.now().isoformat()
        
    return title, first_paragraph, full_content, image_url, published_date_str

def main():
    with app.app_context():
        session = db.session
        source = get_or_create_source(session)
        new_articles_added = 0
        
        html_content = fetch_page_content(URL_BASE)
        if not html_content: return

        soup = BeautifulSoup(html_content, 'html.parser')
        
        unique_links = set()
        for tag in soup.select('.bricks-layout-item a[href]'):
            link = tag['href']
            # Filtro para asegurar que son artículos válidos
            if '/category/' not in link and link.count('/') > 3 and not link.endswith(('/page/2/', '/page/3/')):
                unique_links.add(link)

        print(f"🔍 Encontrados {len(unique_links)} artículos potenciales de '{SOURCE_DISPLAY_NAME}'. Verificando en la BD...")

        for link in unique_links:
            existing_article = session.query(Article).filter_by(link=link).first()
            if existing_article:
                continue

            print(f"\n➕ Procesando noticia nueva: {link}")
            title, first_p, full_content, img_url, published_date_str = scrape_article_details(link)

            if title != "Título no encontrado" and full_content and len(full_content) > 50:
                try:
                    try:
                        published_date = isoparse(published_date_str) if published_date_str else datetime.utcnow()
                    except (ParserError, TypeError):
                        print(f" -> ⚠️  Formato de fecha no reconocido '{published_date_str}', usando fecha actual.")
                        published_date = datetime.utcnow()

                    new_article = Article(
                        title=title,
                        link=link,
                        source_id=source.id,
                        excerpt=first_p,
                        content=full_content,
                        image_url=img_url,
                        status='scraped',
                        published_at=published_date,
                        scraped_at=datetime.utcnow()
                    )
                    
                    session.add(new_article)
                    session.commit()
                    
                    new_articles_added += 1
                    print(f" -> ✅ Noticia (ID: {new_article.id}) guardada en la BD.")

                except Exception as e:
                    print(f" -> ❌ Error al guardar en la BD: {e}")
                    session.rollback()
            else:
                print(f" -> ❌ No se pudo guardar por falta de contenido o título.")
            
            time.sleep(1)

    print(f"\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias nuevas de '{SOURCE_DISPLAY_NAME}'.")

if __name__ == "__main__":
    main()