import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import time

DB_FILE = "noticias.db"
CIUDADES_HUANUCO = [
    # Provincia de Huánuco
    "Huánuco", "Amarilis", "Pillco Marca", "Chinchao", "Margos", "Quisqui", "San Francisco de Cayrán",
    "San Pedro de Chaulán", "Santa María del Valle", "Yarumayo",

    # Provincia de Ambo
    "Ambo", "Cayna", "Colpas", "Conchamarca", "Huácar", "San Francisco", "San Rafael", "Tomay Kichwa",

    # Provincia de Dos de Mayo
    "La Unión", "Chuquis", "Marías", "Pachas", "Quivilla", "Ripán", "Shunqui", "Sillapata", "Yanas",

    # Provincia de Huacaybamba
    "Huacaybamba", "Canchabamba", "Cochabamba", "Pinra",

    # Provincia de Huamalíes
    "Llata", "Arancay", "Chavín de Pariarca", "Jacas Grande", "Jircan", "Miraflores", "Monzón", "Punchao", "Puños", "Singa",

    # Provincia de Leoncio Prado
    "Tingo María", "Daniel Alomía Robles", "Hermilio Valdizán", "José Crespo y Castillo", "Luyando", "Mariano Dámaso Beraun",

    # Provincia de Marañón
    "Huacrachuco", "Cholon", "San Buenaventura",

    # Provincia de Pachitea
    "Panao", "Chaglla", "Molino", "Umari",

    # Provincia de Puerto Inca
    "Puerto Inca", "Codo del Pozuzo", "Honoria", "Tournavista", "Yuyapichis",

    # Provincia de Lauricocha
    "Jesús", "Baños", "San Francisco de Asís", "San Miguel de Cauri", "Queropalca", "Rondos", "Jivia",

    # Provincia de Yarowilca
    "Chavinillo", "Chacabamba", "Cahuac", "Aparicio Pomares", "Choras", "Jacas Chico", "Obas",

    # Otras menciones comunes
    "Acomayo", "Pumahuasi", "Codo del Pozuzo", "Las Moras", "Cauri", "Pillao", "Rupa Rupa"
]


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def fetch_article_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al obtener {url}: {e}")
        return None

def parse_article_details(html_content):
    if not html_content:
        return "Primer párrafo no encontrado."
    soup = BeautifulSoup(html_content, 'html.parser')
    content_div = soup.find('div', class_='entry-content')
    if content_div:
        first_p = content_div.find('p')
        if first_p and first_p.get_text(strip=True):
            return first_p.get_text(strip=True)
    return "Primer párrafo no encontrado."

def find_huanuco_cities(text):
    found = {city for city in CIUDADES_HUANUCO if re.search(r'\b' + re.escape(city) + r'\b', text, re.IGNORECASE)}
    return ", ".join(sorted(found))

def main():
    print("--- Paso 2: Procesando artículos ---")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, link, title FROM articles WHERE status = 'new'")
    articles = cursor.fetchall()

    if not articles:
        print("✅ No hay artículos nuevos por procesar.")
        conn.close()
        return

    for article in articles:
        print(f"📖 Procesando: {article['title']}")
        html = fetch_article_content(article['link'])
        if html:
            paragraph = parse_article_details(html)
            cities = find_huanuco_cities(article['title'] + " " + paragraph)

            cursor.execute("""
                UPDATE articles
                SET first_paragraph = ?, detected_cities = ?, status = 'processed'
                WHERE id = ?
            """, (paragraph, cities, article['id']))
            conn.commit()
            print("  ✅ Párrafo y ciudades guardadas.")
        else:
            cursor.execute("UPDATE articles SET status = 'error_processing' WHERE id = ?", (article['id'],))
            conn.commit()
            print("  ❌ Error al procesar el artículo.")

        time.sleep(0.5)

    conn.close()
    print("--- ✅ Procesamiento completado ---")

if __name__ == "__main__":
    main()
