import sqlite3
import os
import google.generativeai as genai
import json
import time

DB_FILE = "noticias.db"
TABLE_NAME = "articles"

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ No se encontró la variable de entorno GEMINI_API_KEY.")
    exit()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

def analyze_article_with_gemini(title, content):
    prompt = f"""
Eres un analista de noticias experto y un geógrafo preciso. Analiza el siguiente artículo de noticias.
Título: "{title}"
Contenido: "{content}"

Realiza dos tareas:
1. Análisis de Veracidad: Evalúa si la noticia es probablemente verdadera o falsa, con breve razonamiento.
2. Análisis Geográfico: Extrae la ubicación mencionada (País, Región, Provincia, Distrito).

Devuelve tu respuesta SOLO como JSON con esta estructura:
{{
  "veracity_analysis": "Texto...",
  "location": {{
    "country": "País", "region": "Región", "province": "Provincia", "district": "Distrito"
  }}
}}
"""
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        print(f"❌ Error IA o JSON: {e}")
        return None

def main():
    print("--- Paso 3: Analizando con IA ---")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT id, title, first_paragraph FROM {TABLE_NAME} WHERE status = 'processed'")
    articles = cursor.fetchall()

    if not articles:
        print("✅ No hay artículos pendientes de análisis.")
        conn.close()
        return

    for article in articles:
        print(f"🧠 Analizando: {article['title']}")
        result = analyze_article_with_gemini(article['title'], article['first_paragraph'])
        if result:
            try:
                loc = result["location"]
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET analysis_veracity = ?, analysis_country = ?, analysis_region = ?,
                        analysis_province = ?, analysis_district = ?, status = 'analyzed'
                    WHERE id = ?
                """, (
                    result["veracity_analysis"], loc["country"], loc["region"],
                    loc["province"], loc["district"], article["id"]
                ))
                conn.commit()
                print("  ✅ Análisis guardado.")
            except Exception:
                print("  ❌ Error en el formato JSON.")
        time.sleep(1.5)

    conn.close()
    print("--- ✅ Análisis completado ---")

if __name__ == "__main__":
    main()
