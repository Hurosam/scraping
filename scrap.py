import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# URL del sitio a scrapear
URL = "https://tudiariohuanuco.pe/"

# Encabezados para simular una petición de navegador
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_page_content(url):
    """Obtiene el contenido HTML de la página."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        print(f"Página {url} obtenida exitosamente (status: {response.status_code}).")
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la página {url}: {e}")
        return None

def parse_news(html_content):
    """Parsea el contenido HTML y extrae las noticias."""
    if not html_content:
        print("Contenido HTML vacío, no se puede parsear.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    articles_data = []
    processed_links = set()

    # --- Estrategia 1: <article class*='jeg_post'> ---
    print("\n--- Iniciando Estrategia 1: <article class*='jeg_post'> ---")
    articles_jeg_tags = soup.find_all('article', class_=re.compile(r'\bjeg_post\b'))
    print(f"Estrategia 1: Se encontraron {len(articles_jeg_tags)} elementos <article> con clase 'jeg_post'.")

    for article_tag in articles_jeg_tags:
        title_tag = article_tag.find(['h2', 'h3'], class_='jeg_post_title')
        link_tag = title_tag.find('a') if title_tag else None
        excerpt_div = article_tag.find('div', class_='jeg_post_excerpt')
        category_div = article_tag.find('div', class_='jeg_meta_category')

        title = "N/A"
        link = "N/A"
        summary = "N/A"
        category = "N/A"

        if link_tag and link_tag.has_attr('href'):
            title = link_tag.get_text(strip=True)
            link = link_tag['href']
            if not link.startswith('http'):
                link = URL.rstrip('/') + (link if link.startswith('/') else '/' + link)
        
        if excerpt_div:
            p_tag = excerpt_div.find('p')
            if p_tag:
                summary = p_tag.get_text(strip=True)
        
        if category_div:
            cat_link_tag = category_div.find('a')
            if cat_link_tag:
                category = cat_link_tag.get_text(strip=True)

        if link != "N/A" and title != "N/A" and link not in processed_links:
            articles_data.append({
                'title': title,
                'link': link,
                'summary': summary,
                'category': category,
                'source_structure': 'jeg_post'
            })
            processed_links.add(link)

    # --- Estrategia 2: <div class*='tab__post__single--item'> ---
    print("\n--- Iniciando Estrategia 2: <div class*='tab__post__single--item'> ---")
    tab_post_items_tags = soup.find_all('div', class_=lambda c: c and 'tab__post__single--item' in c.split())
    print(f"Estrategia 2: Se encontraron {len(tab_post_items_tags)} elementos <div> con clase 'tab__post__single--item'.")

    for item_div in tab_post_items_tags:
        title_h3 = item_div.find('h3', class_='tab__post--title')
        category_div = item_div.find('div', class_='ekit-post-cat') # Clase común para categoría en estos bloques

        title = "N/A"
        link = "N/A"
        summary = "N/A" 
        category = "N/A"

        if title_h3:
            link_tag_in_h3 = title_h3.find('a')
            if link_tag_in_h3 and link_tag_in_h3.has_attr('href'):
                title = link_tag_in_h3.get_text(strip=True)
                link = link_tag_in_h3['href']
                if not link.startswith('http'):
                    link = URL.rstrip('/') + (link if link.startswith('/') else '/' + link)
        
        # Fallback para el enlace si no está en el h3 (a veces el enlace envuelve la imagen)
        if link == "N/A":
            header_link_tag = item_div.find('a', class_='tab__post--header', href=True)
            if not header_link_tag:
                header_link_tag = item_div.find('a', href=True) # Más genérico
            
            if header_link_tag:
                link = header_link_tag['href']
                if not link.startswith('http'):
                    link = URL.rstrip('/') + (link if link.startswith('/') else '/' + link)
                # Si el título sigue N/A, intentar obtenerlo del alt de la imagen o texto del enlace
                if title == "N/A":
                    img_tag = header_link_tag.find('img', alt=True)
                    if img_tag and img_tag['alt'].strip():
                        title = img_tag['alt'].strip()
                    elif header_link_tag.get_text(strip=True) and header_link_tag.get_text(strip=True) != category: # Evitar que el título sea la categoría
                        title = header_link_tag.get_text(strip=True)


        if category_div:
            cat_link_tag = category_div.find('a')
            if cat_link_tag:
                category = cat_link_tag.get_text(strip=True)

        if link != "N/A" and title != "N/A" and title != category and link not in processed_links: # Evitar si el título es igual a la categoría (suele ser un error de captura)
            articles_data.append({
                'title': title,
                'link': link,
                'summary': summary,
                'category': category,
                'source_structure': 'tab_post_item'
            })
            processed_links.add(link)
        elif link != "N/A" and title == "N/A" and link not in processed_links :
             print(f"    Advertencia (tab_post): Se encontró link {link} pero no título claro. Descartado.")


    # --- Estrategia 3: <div class="hero-content"> ---
    print("\n--- Iniciando Estrategia 3: <div class='hero-content'> ---")
    hero_content_tags = soup.find_all('div', class_='hero-content')
    print(f"Estrategia 3: Se encontraron {len(hero_content_tags)} elementos <div class='hero-content'.")

    for hero_div in hero_content_tags:
        category_tag = hero_div.find('a', class_='post-cat')
        title_h2 = hero_div.find('h2', class_='hero-title')
        p_tag = hero_div.find('p') # Para el resumen

        title = "N/A"
        link = "N/A"
        summary = "N/A"
        category = "N/A"

        if category_tag:
            category = category_tag.get_text(strip=True)
            # A veces el link de la categoría es el mismo que el de la noticia si solo hay una.
            # No usaremos el href de la categoría como link de noticia principal.
        
        if title_h2:
            link_tag_in_h2 = title_h2.find('a')
            if link_tag_in_h2 and link_tag_in_h2.has_attr('href'):
                title = link_tag_in_h2.get_text(strip=True)
                link = link_tag_in_h2['href']
                if not link.startswith('http'):
                    link = URL.rstrip('/') + (link if link.startswith('/') else '/' + link)
        
        if p_tag:
            summary = p_tag.get_text(strip=True)
            if summary == "…": # A veces el resumen es solo "..."
                summary = "..."

        if link != "N/A" and title != "N/A" and link not in processed_links:
            articles_data.append({
                'title': title,
                'link': link,
                'summary': summary,
                'category': category,
                'source_structure': 'hero_content'
            })
            processed_links.add(link)

    if not articles_data:
         print("\nResultado: No se pudo extraer ninguna noticia con las estructuras buscadas y criterios definidos.")
    else:
        print(f"\nResultado: Se procesaron {len(processed_links)} enlaces únicos.")
        
    return articles_data

if __name__ == "__main__":
    print(f"Obteniendo noticias de: {URL}")
    html_content = fetch_page_content(URL)

    if html_content:
        news_items = parse_news(html_content)

        if news_items:
            print(f"\n--------------------------------------------------")
            print(f"Se encontraron {len(news_items)} noticias en total (después de filtrar duplicados e incompletos):\n")
            for i, item in enumerate(news_items, 1):
                print(f"{i}. Título: {item['title']}")
                print(f"   Enlace: {item['link']}")
                print(f"   Categoría: {item['category']}")
                if item['summary'] != "N/A" and item['summary'] != "...":
                    print(f"   Resumen: {item['summary']}")
                # print(f"   (Estructura: {item['source_structure']})") 
                print("-" * 30)

            try:
                df = pd.DataFrame(news_items)
                df = df[['title', 'link', 'category', 'summary', 'source_structure']] # Ordenar columnas
                df.to_csv("noticias_tudiariohuanuco_completo.csv", index=False, encoding='utf-8-sig')
                print("\nNoticias guardadas en 'noticias_tudiariohuanuco_completo.csv'")
            except Exception as e:
                print(f"Error al guardar en CSV: {e}")
        else:
            print("No se pudieron extraer noticias que cumplan los criterios. La estructura de la página pudo haber cambiado o no coincide con los patrones definidos.")
    else:
        print("No se pudo obtener el contenido de la página. Verifique la conexión y la URL.")

    print("\nProceso de scraping finalizado.")