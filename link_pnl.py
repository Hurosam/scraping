import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re # Importar re para el manejo de palabras y normalización

# Nombre del archivo CSV generado por el script anterior
CSV_FILE = "noticias_tudiariohuanuco_completo.csv"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# LISTA DE CIUDADES/LOCALIDADES DE HUÁNUCO (AJUSTAR SEGÚN NECESIDAD)
CIUDADES_HUANUCO = [
    "Huánuco", "Amarilis", "Pillco Marca", "Tomayquichua", "Ambo", "Cayna", "Colpas", "Conchamarca",
    "Huácar", "San Francisco de Mosca", "San Rafael", "Tomay Kichwa", "Dos de Mayo", "La Unión",
    "Chuquis", "Marías", "Pachas", "Quivilla", "Ripán", "Shunqui", "Sillapata", "Yanas",
    "Huacaybamba", "Cochabamba", "Pinra", "Huamalíes", "Llata", "Arancay", "Chavín de Pariarca",
    "Jacas Grande", "Jircan", "Miraflores", "Monzón", "Punchao", "Puños", "Singa", "Tantamayo",
    "Lauricocha", "Jesús", "Baños", "Jivia", "Queropalca", "Rondos", "San Francisco de Asís",
    "San Miguel de Cauri", "Marañón", "Huacrachuco", "Cholon", "San Buenaventura",
    "Pachitea", "Panao", "Chaglla", "Molino", "Umari",
    "Puerto Inca", "Codo del Pozuzo", "Honoria", "Tournavista", "Yuyapichis",
    "Yarowilca", "Chavinillo", "Cáhuac", "Chacabamba", "Choras", "Jacas Chico",
    "Obas", "Pampamarca", "Aparicio Pomares"
    # ... más localidades
]
# Normalizar la lista para la búsqueda (minúsculas y sin tildes si es necesario más adelante)
# Por ahora, la dejamos tal cual para coincidencia exacta, pero considera la normalización.

def fetch_article_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el artículo {url}: {e}")
        return None

def normalize_text_for_search(text):
    """Normaliza el texto: minúsculas y elimina puntuación básica para mejorar la coincidencia."""
    if not text:
        return ""
    text = text.lower()
    # Eliminar puntuación común, se puede expandir
    text = re.sub(r'[^\w\s-]', '', text) # Conserva alfanuméricos, espacios y guiones
    return text

def find_huanuco_cities_in_text(text_to_search, cities_list):
    """
    Busca ciudades de la lista en el texto.
    Devuelve una lista de ciudades encontradas o una lista vacía.
    """
    found_cities = set() # Usar un set para evitar duplicados si una ciudad se menciona varias veces
    if not text_to_search:
        return []

    # Normalizar el texto de búsqueda una vez
    # normalized_text = normalize_text_for_search(text_to_search) # Opcional, depende de la robustez que necesites

    for city in cities_list:
        # Para una coincidencia más robusta, considera buscar la ciudad como una palabra completa
        # y ser insensible a mayúsculas/minúsculas.
        # \b asegura que "Ambo" no coincida con "Ambrosio".
        # re.IGNORECASE hace la búsqueda insensible a mayúsculas/minúsculas.
        if re.search(r'\b' + re.escape(city) + r'\b', text_to_search, re.IGNORECASE):
            found_cities.add(city)
    
    return list(found_cities)


def parse_article_details(html_content, original_title="N/A"):
    if not html_content:
        return original_title, "No se pudo obtener contenido del artículo.", []

    soup = BeautifulSoup(html_content, 'html.parser')
    
    article_title = original_title
    first_paragraph_text = "Primer párrafo no encontrado."
    detected_cities = []

    title_tag_h1 = soup.find('h1', class_=['jeg_post_title', 'entry-title'])
    if title_tag_h1:
        article_title = title_tag_h1.get_text(strip=True)
    else:
        title_tag_h1_generic = soup.find('h1')
        if title_tag_h1_generic:
            article_title = title_tag_h1_generic.get_text(strip=True)

    content_div = soup.find('div', class_='entry-content')
    if content_div:
        inner_content = content_div.find('div', class_='content-inner')
        if inner_content:
            first_p = inner_content.find('p', recursive=False)
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)
            else:
                first_p = inner_content.find('p')
                if first_p and first_p.get_text(strip=True):
                    first_paragraph_text = first_p.get_text(strip=True)
        else:
            first_p = content_div.find('p')
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)

    if first_paragraph_text == "Primer párrafo no encontrado.":
        jeg_content_div = soup.find('div', class_='jeg_inner_content')
        if jeg_content_div:
            actual_content_area = jeg_content_div.find('div', class_='content-inner')
            if not actual_content_area :
                 actual_content_area = jeg_content_div
            first_p = actual_content_area.find('p')
            if first_p and first_p.get_text(strip=True):
                first_paragraph_text = first_p.get_text(strip=True)

    if first_paragraph_text == "Primer párrafo no encontrado.":
        article_body = soup.find('article')
        if article_body:
            first_p = article_body.find('p')
            if first_p and first_p.get_text(strip=True):
                if len(first_p.get_text(strip=True)) > 50:
                    first_paragraph_text = first_p.get_text(strip=True)
                else:
                    all_p = article_body.find_all('p')
                    if len(all_p) > 1 and all_p[1].get_text(strip=True) and len(all_p[1].get_text(strip=True)) > 50:
                         first_paragraph_text = all_p[1].get_text(strip=True)
    
    # --- BÚSQUEDA DE CIUDADES ---
    # Combinar título y primer párrafo para la búsqueda
    text_to_analyze = article_title
    if first_paragraph_text != "Primer párrafo no encontrado.":
        text_to_analyze += " " + first_paragraph_text
    
    detected_cities = find_huanuco_cities_in_text(text_to_analyze, CIUDADES_HUANUCO)

    return article_title, first_paragraph_text, detected_cities

if __name__ == "__main__":
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print(f"Error: El archivo '{CSV_FILE}' no fue encontrado.")
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
        original_title_from_csv = row.get('title', 'Título no disponible en CSV')

        print(f"Procesando: {article_url}")
        
        html_article = fetch_article_content(article_url)
        
        if html_article:
            title, first_paragraph, cities = parse_article_details(html_article, original_title_from_csv)
            
            print(f"  Título: {title}")
            print(f"  Primer Párrafo: {first_paragraph}")
            if cities:
                print(f"  Ciudades de Huánuco detectadas: {', '.join(cities)}")
            else:
                print(f"  Ciudades de Huánuco detectadas: Ninguna")
            print("-" * 30 + "\n")
            
            all_articles_details.append({
                'original_csv_title': original_title_from_csv,
                'scraped_article_title': title,
                'link': article_url,
                'first_paragraph': first_paragraph,
                'detected_huanuco_cities': ', '.join(cities) if cities else None # Guardar como string o None
            })
        else:
            print(f"  No se pudo obtener contenido para: {article_url}\n")
            all_articles_details.append({
                'original_csv_title': original_title_from_csv,
                'scraped_article_title': "Error al obtener",
                'link': article_url,
                'first_paragraph': "Error al obtener",
                'detected_huanuco_cities': None
            })
        
        # time.sleep(0.2) # Pausa ligera

    if all_articles_details:
        output_df = pd.DataFrame(all_articles_details)
        # Reordenar columnas si es necesario
        output_df = output_df[['original_csv_title', 'scraped_article_title', 'link', 'first_paragraph', 'detected_huanuco_cities']]
        output_csv_file = "articulos_con_parrafo_y_ciudades.csv"
        try:
            output_df.to_csv(output_csv_file, index=False, encoding='utf-8-sig')
            print(f"\nResultados guardados en '{output_csv_file}'")
        except Exception as e:
            print(f"Error al guardar los detalles de artículos en CSV: {e}")

    print("\nProceso de extracción de detalles y ciudades de artículos finalizado.")