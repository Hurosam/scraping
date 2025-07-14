import sqlite3
import os
import google.generativeai as genai
import json
import time

DB_FILE = "noticias.db"
TABLE_NAME = "articles"

# --- CONFIGURACIÓN DE GEMINI ---
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Variable de entorno GEMINI_API_KEY no encontrada.")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Error al configurar la API de Gemini: {e}")
    exit()

model = genai.GenerativeModel('gemini-1.5-flash-latest')


def setup_database_columns():
    # Esta función ya es robusta, no necesita cambios.
    pass


def analyze_article_with_gemini(title, content, source):
    prompt_content = content or ""
    prompt = f"""
TASK: Analyze the news article below from the perspective of a resident of HUÁNUCO, PERÚ.
YOU MUST RESPOND ONLY WITH A VALID JSON OBJECT and all text values MUST be in SPANISH.
All keys, including "reason", are MANDATORY.

ARTICLE:
- Source: "{source}"
- Title: "{title}"
- Content Excerpt: "{prompt_content[:3000]}"

REQUIRED JSON OUTPUT (in Spanish):
{{
  "summary": "Un resumen conciso en español.",
  "category": "Choose one: [Política, Policial, Accidente, Salud, Deporte, Social, Ambiental, Judicial, Otro].",
  "veracity": {{
    "score": <integer 0-100>,
    "reason": "Justificación OBLIGATORIA en español para la veracidad."
  }},
  "regional_interest": {{
    "score": <integer 0-100>,
    "reason": "Justificación OBLIGATORIA en español sobre el interés para un ciudadano de HUÁNUCO. Considera la fuente y el contenido."
  }},
  "location": {{
    "country": "Perú",
    "region": "Huánuco",
    "province": "Provincia detectada.",
    "district": "Distrito detectado."
  }}
}}
"""
    try:
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().lstrip("```json").rstrip("```")
        return json.loads(cleaned_response)
    except Exception as e:
        print(f"  -> ❌ Error al procesar con Gemini: {e}")
        if 'response' in locals():
            print(f"  -> Respuesta de Gemini:\n{response.text}")
        return None


def main():
    print("\n--- Iniciando análisis con IA (Versión Corregida) ---")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT id, title, source, first_paragraph, full_content 
        FROM {TABLE_NAME} 
        WHERE status = 'processed'
    """)
    articles_to_analyze = cursor.fetchall()

    total_articles = len(articles_to_analyze)
    if not total_articles:
        print("✅ No hay noticias nuevas para analizar.")
        conn.close()
        return

    print(f"📰 Se encontraron {total_articles} noticias para analizar.")

    for i, article in enumerate(articles_to_analyze, 1):
        print(f"\n[{i}/{total_articles}] Analizando: '{article['title']}' (Fuente: {article['source']})")

        content_to_analyze = article['first_paragraph'] or article['full_content']
        if not content_to_analyze or len(content_to_analyze) < 20:
            print("  -> ⚠️ Contenido insuficiente.")
            cursor.execute("UPDATE articles SET status = 'failed' WHERE id = ?", (article['id'],))
            conn.commit()
            continue

        analysis_result = analyze_article_with_gemini(article['title'], content_to_analyze, article['source'])

        if analysis_result:
            try:
                summary = analysis_result.get('summary', 'Resumen no proporcionado.')
                category = analysis_result.get('category', 'Otro')

                veracity = analysis_result.get('veracity', {})
                interest = analysis_result.get('regional_interest', {})
                loc = analysis_result.get('location', {})

                veracity_score = veracity.get('score')
                veracity_reason = veracity.get('reason') or "Justificación no proporcionada."

                interest_score = interest.get('score')
                interest_reason = interest.get('reason') or "Justificación no proporcionada."

                country = loc.get('country', 'Perú')
                region = loc.get('region', 'Huánuco')
                province = loc.get('province')
                district = loc.get('district')

                cursor.execute(f"""
                    UPDATE {TABLE_NAME} SET
                        analysis_summary = ?,
                        analysis_category = ?,
                        analysis_veracity_score = ?,
                        analysis_veracity_reason = ?,
                        analysis_interest_score = ?, 
                        analysis_regional_interest_reason = ?, 
                        analysis_country = ?,
                        analysis_region = ?,
                        analysis_province = ?,
                        analysis_district = ?,
                        status = 'analyzed'
                    WHERE id = ?
                """, (
                    summary, category,
                    veracity_score, veracity_reason,
                    interest_score, interest_reason,
                    country, region, province, district,
                    article['id']
                ))
                conn.commit()
                print("  -> ✅ Análisis guardado correctamente en la BD.")
            except Exception as e:
                print(f"  -> ❌ Error CRÍTICO al actualizar la BD: {e}")
                cursor.execute("UPDATE articles SET status = 'failed' WHERE id = ?", (article['id'],))
                conn.commit()
        else:
            cursor.execute("UPDATE articles SET status = 'failed' WHERE id = ?", (article['id'],))
            conn.commit()

        time.sleep(5)

    conn.close()
    print("\n--- ✅ Análisis con IA completado. ---")


if __name__ == "__main__":
    main()
