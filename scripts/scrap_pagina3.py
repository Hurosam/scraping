# --- START OF FILE scripts/scrap_pagina3.py ---

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
URL_BASE = "https://pagina3.pe"
SOURCE_NAME_KEY = "pagina3_huanuco"
SOURCE_DISPLAY_NAME = "Página3 Huánuco"
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
    """Extrae los detalles de una página de artículo de Pagina3."""
    html_content = fetch_page_content(article_url)
    if not html_content:
        return None, None, None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    title_tag = soup.select_one('h1.entry-title')
    title = title_tag.get_text(strip=True) if title_tag else "Título no encontrado"
    
    first_paragraph, full_content = None, None
    content_container = soup.select_one('div.entry-content')
    if content_container:
        paragraphs = [p.get_text(strip=True) for p in content_container.find_all('p') if p.get_text(strip=True)]
        if paragraphs:
            first_paragraph = paragraphs[0]
            full_content = '\n'.join(paragraphs)

    image_url = None
    og_image_tag = soup.find('meta', property='og:image')
    if og_image_tag and og_image_tag.get('content'):
        image_url = og_image_tag['content']
    else:
        img_tag = soup.select_one('.post-thumbnail img, .entry-content img')
        if img_tag: image_url = img_tag.get('src')
    
    published_date_str = None
    time_tag = soup.select_one('time.entry-date[datetime]')
    if time_tag and time_tag.get('datetime'):
        published_date_str = time_tag['datetime']
    
    if not published_date_str:
        published_date_str = datetime.now().isoformat()
        
    return title, first_paragraph, full_content, image_url, published_date_str

def main():
    with app.app_context():
        session = db.session
        source = get_or_create_source(session)
        new_articles_added = 0
        processed_links = 0
        
        html_content = fetch_page_content(URL_BASE)
        if not html_content: return

        soup = BeautifulSoup(html_content, 'html.parser')
        
        article_link_selectors = [
            '.category-slide-post-title a',
            '.multi-category-post-title a',
            '.blog-category-post-title a'
        ]
        
        # ✅ CAMBIO: Se añade un filtro para ignorar URLs no deseadas como '/ordenanzas/'
        links_to_process = {
            tag['href'] for selector in article_link_selectors 
            for tag in soup.select(selector) 
            if tag.has_attr('href') and '/ordenanzas/' not in tag['href']
        }

        print(f"🔍 Encontrados {len(links_to_process)} artículos potenciales de '{SOURCE_DISPLAY_NAME}'. Verificando en la BD...")

        for link in links_to_process:
            processed_links += 1
            
            # Imprimir progreso para no parecer que está colgado
            print(f"\r[{processed_links}/{len(links_to_process)}] Procesando...", end="")

            existing_article = session.query(Article).filter_by(link=link).first()
            if existing_article:
                continue

            
            title, first_p, full_content, img_url, published_date_str = scrape_article_details(link)

            if title != "Título no encontrado" and full_content and len(full_content) > 50:
                print(f"\n➕ Encontrada noticia nueva: {title[:50]}...") # Salto de línea solo para noticias nuevas
                try:
                    try:
                        published_date = isoparse(published_date_str) if published_date_str else datetime.utcnow()
                    except (ParserError, TypeError):
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
            
            time.sleep(1)

    print(f"\n\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias nuevas de '{SOURCE_DISPLAY_NAME}'.")

if __name__ == "__main__":
    main()