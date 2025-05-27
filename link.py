import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Nombre del archivo CSV generado por el script anterior
CSV_FILE = "noticias_tudiariohuanuco_completo.csv" # Asegúrate que este nombre coincida

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_article_content(url):
    """Obtiene el contenido HTML de una página de artículo."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el artículo {url}: {e}")
        return None

def parse_article_details(html_content, original_title="N/A"):
    """
    Parsea el contenido HTML de una página de artículo para extraer el título
    y el primer párrafo del contenido principal.
    """
    if not html_content:
        return original_title, "No se pudo obtener contenido del artículo."

    soup = BeautifulSoup(html_content, 'html.parser')
    
    article_title = original_title
    first_paragraph_text = "Primer párrafo no encontrado."

    # --- Estrategia para el Título (confirmar o mejorar el del CSV) ---
    # Los títulos suelen estar en <h1> dentro de la entrada principal
    title_tag_h1 = soup.find('h1', class_=['jeg_post_title', 'entry-title']) # Clases comunes para títulos de post
    if title_tag_h1:
        article_title = title_tag_h1.get_text(strip=True)
    else: # Fallback si no hay h1 con esas clases específicas
        title_tag_h1_generic = soup.find('h1')
        if title_tag_h1_generic:
            article_title = title_tag_h1_generic.get_text(strip=True)

    # --- Estrategia para el Contenido Principal y Primer Párrafo ---
    # El contenido principal suele estar en un div con clase 'entry-content', 'post-content', 'content-inner', etc.
    # Para TuDiarioHuanuco, 'jeg_inner_content' o 'content-inner' parecen ser las más probables.
    
    # Prioridad 1: 'div.entry-content .content-inner > p' (estructura común en JNews)
    content_div = soup.find('div', class_='entry-content')
    if content_div:
        # A veces hay divs anidados antes del contenido real
        inner_content = content_div.find('div', class_='content-inner') # Común en tema JNews
        if inner_content:
            first_p = inner_content.find('p', recursive=False) # Busca <p> directamente dentro de content-inner
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)
            else: # Si no hay un <p> directo, buscar el primer <p> en general
                first_p = inner_content.find('p')
                if first_p and first_p.get_text(strip=True):
                  first_paragraph_text = first_p.get_text(strip=True)
        else: # Si no hay 'content-inner', buscar directamente en 'entry-content'
            first_p = content_div.find('p')
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)

    # Fallback: Buscar en 'div.jeg_inner_content' (otra estructura de JNews)
    if first_paragraph_text == "Primer párrafo no encontrado.":
        jeg_content_div = soup.find('div', class_='jeg_inner_content')
        if jeg_content_div:
            # Dentro de jeg_inner_content, el contenido puede estar en 'div.content-inner'
            actual_content_area = jeg_content_div.find('div', class_='content-inner')
            if not actual_content_area : # O directamente
                 actual_content_area = jeg_content_div

            first_p = actual_content_area.find('p')
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)

    # Fallback más genérico si las clases específicas no funcionan
    if first_paragraph_text == "Primer párrafo no encontrado.":
        # Buscar dentro de <article> tags, y luego el primer <p>
        article_body = soup.find('article') # Busca el primer <article> tag
        if article_body:
            first_p = article_body.find('p')
            if first_p and first_p.get_text(strip=True):
                # Evitar párrafos muy cortos o que sean solo créditos de fotos, etc.
                if len(first_p.get_text(strip=True)) > 50: # Umbral simple
                    first_paragraph_text = first_p.get_text(strip=True)
                else:
                    # Intentar el segundo párrafo si el primero es muy corto
                    all_p = article_body.find_all('p')
                    if len(all_p) > 1 and all_p[1].get_text(strip=True) and len(all_p[1].get_text(strip=True)) > 50:
                         first_paragraph_text = all_p[1].get_text(strip=True)


    # Limpieza: a veces los párrafos comienzan con el nombre del reportero o la ciudad en mayúsculas
    # Esto es opcional y puede necesitar ajuste
    # if first_paragraph_text.isupper() and len(first_paragraph_text.split()) < 5:
    #     # Podría ser un encabezado de ubicación/autor, buscar el siguiente párrafo
    #     pass # Lógica más compleja aquí si es necesario

    return article_title, first_paragraph_text

if __name__ == "__main__":
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"Error: El archivo '{CSV_FILE}' no fue encontrado.")
        print("Asegúrate de que el script de scraping principal se haya ejecutado y generado el CSV.")
        exit()
    except Exception as e:
        print(f"Error al leer el archivo CSV '{CSV_FILE}': {e}")
        exit()

    if 'link' not in df.columns:
        print(f"Error: La columna 'link' no se encontró en '{CSV_FILE}'.")
        exit()

    print(f"Procesando artículos desde '{CSV_FILE}'...\n")
    
    all_articles_details = []

    for index, row in df.iterrows():
        article_url = row['link']
        original_title_from_csv = row.get('title', 'Título no disponible en CSV') # Usar get por si la columna title no existe

        print(f"Procesando: {article_url}")
        
        html_article = fetch_article_content(article_url)
        
        if html_article:
            title, first_paragraph = parse_article_details(html_article, original_title_from_csv)
            
            print(f"  Título: {title}")
            print(f"  Primer Párrafo: {first_paragraph}\n")
            
            all_articles_details.append({
                'original_csv_title': original_title_from_csv,
                'scraped_article_title': title,
                'link': article_url,
                'first_paragraph': first_paragraph
            })
        else:
            print(f"  No se pudo obtener contenido para: {article_url}\n")
            all_articles_details.append({
                'original_csv_title': original_title_from_csv,
                'scraped_article_title': "Error al obtener",
                'link': article_url,
                'first_paragraph': "Error al obtener"
            })
        
        # Pausa opcional para no sobrecargar el servidor
        # time.sleep(0.5) # 0.5 segundos de pausa entre peticiones

    # Opcional: Guardar los resultados en un nuevo CSV
    if all_articles_details:
        output_df = pd.DataFrame(all_articles_details)
        output_csv_file = "articulos_con_primer_parrafo.csv"
        try:
            output_df.to_csv(output_csv_file, index=False, encoding='utf-8-sig')
            print(f"\nResultados guardados en '{output_csv_file}'")
        except Exception as e:
            print(f"Error al guardar los detalles de artículos en CSV: {e}")

    print("\nProceso de extracción de detalles de artículos finalizado.")