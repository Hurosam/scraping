# --- START OF FILE scripts/scrap_diariocorreo.py ---

import sys
import os
# ✅ CAMBIO 1: Añadimos la ruta del proyecto al path de Python
# Esto es CRUCIAL para que el script pueda encontrar e importar el módulo 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import time
from dateutil.parser import isoparse, ParserError

# ✅ CAMBIO 2: Importamos los componentes de nuestra aplicación Flask
from app import create_app
from app.extensions import db
from app.models import Article, NewsSource

# ✅ CAMBIO 3: Creamos una instancia de la aplicación Flask para obtener su contexto
app = create_app()

# --- Constantes del Scraper (sin cambios) ---
URL_BASE = "https://diariocorreo.pe"
URL_HUANUCO = f"{URL_BASE}/archivo/edicion/huanuco/"
SOURCE_NAME_KEY = "diario_correo" # Usaremos el 'name' (clave interna) para buscar
SOURCE_DISPLAY_NAME = "Diario Correo"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# ✅ CAMBIO 4: La función get_source_id es reemplazada por una que usa SQLAlchemy
def get_or_create_source(session):
    """
    Busca la fuente de noticias en la BD. Si no existe, la crea.
    Usa la sesión de SQLAlchemy en lugar de una conexión directa.
    """
    source = session.query(NewsSource).filter_by(name=SOURCE_NAME_KEY).first()
    if not source:
        print(f"Fuente '{SOURCE_DISPLAY_NAME}' no encontrada, creándola...")
        source = NewsSource(name=SOURCE_NAME_KEY, display_name=SOURCE_DISPLAY_NAME)
        session.add(source)
        session.commit()
    return source

def fetch_page_content(url):
    """Obtiene el contenido HTML de una URL. (Sin cambios)"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener la página {url}: {e}")
        return None

def scrape_article_details(article_url):
    """Extrae los detalles de una página de artículo. (Sin cambios)"""
    html_content = fetch_page_content(article_url)
    if not html_content:
        return None, None, None, None, None
    # ... (el resto del código de esta función es idéntico al tuyo)
    soup = BeautifulSoup(html_content, 'html.parser')
    title = (soup.select_one('h1.sht__title, h1.story-content__title').get_text(strip=True) 
             if soup.select_one('h1.sht__title, h1.story-content__title') else "Título no encontrado")
    first_paragraph, full_content = None, None
    content_container = soup.select_one('div.story-body__content, div.story-contents__content')
    if content_container:
        for unwanted in content_container.select('div[data-ad-id], div.contenedorTruvidPos, a > strong'):
            unwanted.decompose()
        paragraphs = [p.get_text(strip=True) for p in content_container.find_all('p') if p.get_text(strip=True) and "MIRA ESTO:" not in p.get_text()]
        if paragraphs:
            first_paragraph = paragraphs[0]
            full_content = '\n'.join(paragraphs)
    image_url = None
    og_image_tag = soup.find('meta', property='og:image')
    if og_image_tag and og_image_tag.get('content'):
        image_url = og_image_tag.get('content')
    else:
        img_tag = soup.select_one('figure.s-multimedia__image--big img, div.story-header__media img')
        if img_tag:
            image_url = img_tag.get('src') or img_tag.get('data-src')
            if image_url and not image_url.startswith('http'):
                image_url = urljoin(URL_BASE, image_url)
    published_date = None
    time_tag = soup.select_one('time.story-contents__author-date[datetime], time.sht__time[datetime]')
    if time_tag and time_tag.get('datetime'):
        published_date = time_tag['datetime']
    if not published_date:
        meta_date_tag = soup.find('meta', property='article:published_time')
        if meta_date_tag and meta_date_tag.get('content'):
            published_date = meta_date_tag['content']
    if not published_date:
        published_date = datetime.now().isoformat()
    return title, first_paragraph, full_content, image_url, published_date

def main():
    # ✅ CAMBIO 5: Se utiliza el 'app_context' de Flask para todas las operaciones de BD
    with app.app_context():
        session = db.session # Obtenemos la sesión de SQLAlchemy
        source = get_or_create_source(session)
        new_articles_added = 0
        
        html_content = fetch_page_content(URL_HUANUCO)
        if not html_content: return

        soup = BeautifulSoup(html_content, 'html.parser')
        article_containers = soup.select('div.story-item')
        print(f"🔍 Encontrados {len(article_containers)} artículos potenciales. Verificando en la BD...")

        for item in article_containers:
            title_tag = item.select_one('a.story-item__title')
            if not title_tag: continue
            
            full_link = urljoin(URL_BASE, title_tag['href'])

            # ✅ CAMBIO 6: La consulta de existencia ahora usa SQLAlchemy
            existing_article = session.query(Article).filter_by(link=full_link).first()
            if existing_article: continue

            print(f"\n➕ Procesando noticia nueva: {title_tag.get_text(strip=True)}")
            title, first_p, full_content, img_url, published_date_str = scrape_article_details(full_link)

            if title != "Título no encontrado" and full_content and len(full_content) > 100:
                try:
                    # Parsear la fecha de forma segura
                    try:
                        published_date = isoparse(published_date_str) if published_date_str else datetime.utcnow()
                    except ParserError:
                        print(f" -> ⚠️  Formato de fecha no reconocido '{published_date_str}', usando fecha actual.")
                        published_date = datetime.utcnow()
                    
                    # ✅ CAMBIO 7: La inserción de datos ahora es a través de un objeto Modelo
                    new_article = Article(
                        title=title,
                        link=full_link,
                        source_id=source.id,
                        excerpt=first_p,
                        content=full_content,
                        image_url=img_url, # El proxy del frontend se encargará de esto
                        status='scraped',
                        published_at=published_date,
                        scraped_at=datetime.utcnow()
                    )
                    
                    session.add(new_article)
                    session.commit() # Guardamos el objeto en la base de datos
                    
                    new_articles_added += 1
                    print(f" -> ✅ Noticia (ID: {new_article.id}) guardada en la BD.")

                except Exception as e:
                    print(f" -> ❌ Error al guardar en la BD: {e}")
                    session.rollback() # Revertimos los cambios si hay un error
            else:
                print(f" -> ❌ No se pudo guardar por falta de contenido o título.")

            time.sleep(1)

    print(f"\n💾 Proceso finalizado. Se añadieron {new_articles_added} noticias de '{SOURCE_DISPLAY_NAME}'.")

if __name__ == "__main__":
    print(f"\n=== Iniciando scraping de: {SOURCE_NAME_DISPLAY_NAME} ===")
    main()