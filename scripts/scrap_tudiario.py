# --- START OF FILE scripts/scrap_tudiario.py ---

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import time
import re
from dateutil.parser import isoparse, ParserError

from app import create_app
from app.extensions import db
from app.models import Article, NewsSource

app = create_app()

URL = "https://tudiariohuanuco.pe/"
SOURCE_NAME_KEY = "tu_diario_huanuco"
SOURCE_DISPLAY_NAME = "Tu Diario Huánuco"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def parse_spanish_date(date_string):
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    try:
        date_string_lower = date_string.lower().strip()
        match = re.search(r'(\d{1,2})\s+(\w+),\s+(\d{4})', date_string_lower)
        if match:
            day, month_name, year = match.groups()
            month_num = meses.get(month_name)
            if month_num:
                return datetime(int(year), month_num, int(day)).isoformat()
    except Exception:
        return None
    return None

def get_or_create_source(session):
    source = session.query(NewsSource).filter_by(name=SOURCE_NAME_KEY).first()
    if not source:
        print(f"Fuente '{SOURCE_DISPLAY_NAME}' no encontrada, creándola...")
        source = NewsSource(name=SOURCE_NAME_KEY, display_name=SOURCE_DISPLAY_NAME)
        session.add(source)
        session.commit()
    return source

def fetch_page_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página {url}: {e}")
        return None

def scrape_article_details(article_url):
    html_content = fetch_page_content(article_url)
    if not html_content: return None, None, None, None, None

    soup = BeautifulSoup(html_content, 'html.parser')
    
    title_tag = soup.select_one('h1.post-title')
    title = title_tag.get_text(strip=True) if title_tag else "Título no encontrado"
    
    first_paragraph, full_content = None, None
    content_container = soup.select_one('div.entry-content')
    if content_container:
        for unwanted in content_container.select('script, style, .afw, .xs_social_share_widget, .contenedorTruvidPos'):
            unwanted.decompose()
        paragraphs = [p.get_text(strip=True) for p in content_container.find_all('p') if p.get_text(strip=True)]
        if paragraphs:
            first_paragraph = paragraphs[0]
            full_content = '\n'.join(paragraphs)

    image_url = None
    image_tag = soup.select_one('div.entry-thumbnail img')
    if image_tag and image_tag.has_attr('src'):
        image_url = image_tag['src']
    else:
        og_image_tag = soup.find('meta', property='og:image')
        if og_image_tag and og_image_tag.get('content'):
            image_url = og_image_tag.get('content')
    
    published_date_str = None
    meta_date_tag = soup.find('meta', property='article:published_time')
    if meta_date_tag and meta_date_tag.get('content'):
        published_date_str = meta_date_tag['content']
    
    if not published_date_str:
        visible_date_tag = soup.select_one('.post-meta-info li:has(i.xsicon-clock)')
        if visible_date_tag:
            date_string = visible_date_tag.get_text(strip=True)
            published_date_str = parse_spanish_date(date_string)

    if not published_date_str:
        published_date_str = datetime.now().isoformat()
        
    return title, first_paragraph, full_content, image_url, published_date_str

def main():
    with app.app_context():
        session = db.session
        source = get_or_create_source(session)
        new_articles_added = 0
        
        html_content = fetch_page_content(URL)
        if not html_content: return

        soup = BeautifulSoup(html_content, 'html.parser')
        
        selectors = ['div.tab__post__single--item a', 'div.hero-content a', 'div.ts-overlay-style a', 'div.ts-col-box-item a']
        unique_links = {
            tag['href'] for selector in selectors 
            for tag in soup.select(selector) 
            if tag.has_attr('href') and 'tudiariohuanuco.pe' in tag['href'] and '/categoria/' not in tag['href']
        }

        print(f"🔍 Encontrados {len(unique_links)} artículos potenciales. Verificando en la BD...")

        for link in unique_links:
            existing_article = session.query(Article).filter_by(link=link).first()
            if existing_article: continue

            print(f"\n➕ Procesando noticia nueva: {link}")
            title, first_p, full_content, img_url, published_date_str = scrape_article_details(link)

            if title != "Título no encontrado" and full_content and len(full_content) > 100:
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
                    print(f" -> ✅ Noticia '{title[:40]}...' guardada en la BD.")
                except Exception as e:
                    print(f" -> ❌ Error al guardar en la BD: {e}")
                    session.rollback()
            else:
                print(f" -> ❌ No se pudo guardar por falta de contenido o título.")

            time.sleep(1)

    print(f"\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias nuevas de '{SOURCE_DISPLAY_NAME}'.")

if __name__ == "__main__":
    print(f"\n=== Iniciando scraping de: {SOURCE_DISPLAY_NAME} ===")
    main()