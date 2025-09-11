# --- START OF FILE scripts/analyze_news.py ---

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import google.generativeai as genai
import json
import time
from datetime import datetime
import re
from sqlalchemy.orm import joinedload

from app import create_app
from app.extensions import db
from app.models import Article, ArticleAnalysis, Category, Location, Tag, NewsSource

app = create_app()

# --- CONFIGURACIÓN DE GEMINI ---
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Variable de entorno GEMINI_API_KEY no encontrada.")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"❌ Error al configurar la API de Gemini: {e}")
    exit()


class NewsAnalyzer:
    def __init__(self):
        self.processed_articles = 0
        self.failed_articles = 0
        self.errors = []
        
    def get_category_id(self, session, category_name):
        if not category_name: return None
        category = session.query(Category).filter_by(name=category_name).first()
        if not category:
            category = Category(name=category_name)
            session.add(category)
            session.commit()
        return category.id

    def get_location_id(self, session, location_name, location_type='province'):
        if not location_name: return None
        location = session.query(Location).filter(Location.name.ilike(f'%{location_name}%'), Location.type == location_type).first()
        return location.id if location else None

    def extract_entities(self, content):
        entities = {'people': [], 'organizations': [], 'events': []}
        people_patterns = [r'(?:Sr\.|Sra\.|Dr\.|Dra\.|Ing\.|Prof\.|Lic\.|Alcalde|Alcaldesa|Presidente|Presidenta|Ministro|Ministra|Fiscal|Juez|Jueza)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)', r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)']
        for pattern in people_patterns: matches = re.findall(pattern, content); entities['people'].extend(matches)
        org_patterns = [r'(?:Municipalidad|Hospital|Clínica|Universidad|Instituto|Colegio|Empresa|Corporación|Fundación)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)', r'(?:PNP|MINSA|MINEDU|MEF|INDECI|SERNANP)']
        for pattern in org_patterns: matches = re.findall(pattern, content); entities['organizations'].extend(matches)
        for key in entities: entities[key] = list(set([e.strip() for e in entities[key] if len(e.strip()) > 3]))
        return entities
    
    def analyze_article_with_gemini(self, article):
        content_to_analyze = (article.content or article.excerpt or '')[:4000]
        
        # ✅ PROMPT COMPLETO RESTAURADO
        prompt = f"""
INSTRUCCIONES: Actúa como un analista de medios de comunicación para la región de Huánuco, Perú. Tu objetivo es clasificar el impacto de cada noticia para un ciudadano local.
RESPONDE ÚNICAMENTE CON UN OBJETO JSON VÁLIDO. Todos los valores de texto DEBEN estar en ESPAÑOL.

ARTÍCULO:
- Título: "{article.title}"
- Contenido: "{content_to_analyze}"

RESPUESTA REQUERIDA (JSON):
{{
  "summary": "Resumen ejecutivo de 2-3 oraciones, destacando los hechos clave y actores involucrados.",
  "category": "Elige UNA: [Política, Policial, Accidente, Salud, Deporte, Social, Ambiental, Judicial, Economía, Educación, Otro]",
  "veracity": {{ "score": <entero 0-100>, "confidence": <decimal 0.0-1.0>, "reasoning": "Evalúa la credibilidad de la noticia. ¿Cita fuentes oficiales? ¿Presenta evidencia o es un rumor? ¿Parece objetiva?" }},
  "popular_interest": {{
    "score": <entero 0-100>,
    "reasoning": "Evalúa el interés general y el potencial de ser un tema de conversación popular. Se enfoca en entretenimiento, cultura, deportes, eventos sociales y curiosidades. Ejemplo: Un concierto, el resultado de un partido de fútbol, o un festival local."
  }},
  "civic_impact": {{
    "score": <entero 0-100>,
    "reasoning": "Evalúa cómo la noticia afecta directamente la seguridad, el bienestar y la vida cotidiana de los ciudadanos. Se enfoca en temas que alteran la tranquilidad y el orden público. Ejemplo: Un accidente de tránsito grave, un asalto, una estafa reportada, una muerte violenta, o una falla en un servicio público esencial (agua, luz)."
  }},
  "location": {{
    "province": "Provincia de Huánuco más relevante (ej: 'Huánuco', 'Leoncio Prado') o null."
  }},
  "key_topics": ["Lista de 3-5 palabras o frases clave para indexación y búsqueda."]
}}

IMPORTANTE:
Una noticia puede tener alto 'popular_interest' pero bajo 'civic_impact' (ej. un festival).
Una noticia puede tener alto 'civic_impact' y también alto 'popular_interest' (ej. un crimen impactante que está en boca de todos).
Tu análisis debe diferenciar claramente estos dos tipos de impacto.
"""
        try:
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            analysis_data = json.loads(response.text)
            if not isinstance(analysis_data, dict):
                raise ValueError(f"La respuesta de la IA no es un diccionario, sino {type(analysis_data)}")
            
            required_fields = ['summary', 'category', 'veracity', 'popular_interest', 'civic_impact']
            for field in required_fields:
                if field not in analysis_data:
                    raise ValueError(f"Campo requerido '{field}' no encontrado en la respuesta")
            return analysis_data
        except Exception as e:
            print(f"  ❌ Error en análisis con Gemini: {e}")
            if 'response' in locals():
                print(f"  🔍 Respuesta recibida: {response.text[:200]}...")
            return None
    
    def save_analysis_to_db(self, session, article_id, analysis_data, entities):
        try:
            category_id = self.get_category_id(session, analysis_data.get('category'))
            location_data = analysis_data.get('location', {})
            province = location_data.get('province')
            primary_location_id = self.get_location_id(session, province) if province else None
            
            veracity = analysis_data.get('veracity', {})
            popular_interest = analysis_data.get('popular_interest', {})
            civic_impact = analysis_data.get('civic_impact', {})
            
            key_topics = analysis_data.get('key_topics', [])

            existing_analysis = session.query(ArticleAnalysis).filter_by(article_id=article_id).first()
            if existing_analysis:
                analysis_record = existing_analysis
            else:
                analysis_record = ArticleAnalysis(article_id=article_id)

            # ✅ CAMPOS COMPLETOS RESTAURADOS
            analysis_record.summary = analysis_data.get('summary')
            analysis_record.category_id = category_id
            analysis_record.primary_location_id = primary_location_id
            analysis_record.veracity_score = veracity.get('score')
            analysis_record.local_relevance_score = popular_interest.get('score')
            analysis_record.civic_impact_score = civic_impact.get('score')
            # (Aquí añadirías más campos si tu modelo ArticleAnalysis los tuviera, como veracity_reasoning, etc.)

            if not existing_analysis:
                session.add(analysis_record)

            article_to_update = session.query(Article).get(article_id)
            if article_to_update:
                article_to_update.status = 'analyzed'
                if key_topics:
                    self.save_article_tags(session, article_to_update, key_topics)
            
            session.commit()
            return True
        except Exception as e:
            print(f"  ❌ Error guardando análisis en BD: {e}")
            session.rollback()
            return False

    def save_article_tags(self, session, article, topics):
        if not article: return
        
        article.tags.clear()
        for topic_name in topics:
            if not topic_name or len(topic_name.strip()) < 2: continue
            
            slug = topic_name.strip().lower().replace(' ', '-')
            tag = session.query(Tag).filter_by(slug=slug).first()
            if not tag:
                tag = Tag(name=topic_name.strip(), slug=slug)
                session.add(tag)
                # No es necesario cometer aquí, se hará al final de save_analysis_to_db
            
            if tag not in article.tags:
                article.tags.append(tag)
    
    def run_analysis(self):
        with app.app_context():
            session = db.session
            print("\n=== Iniciando análisis con IA (v4.0 - SQLAlchemy Completo) ===")
            
            articles_to_analyze = session.query(Article)\
                .options(joinedload(Article.source))\
                .filter(Article.status == 'scraped').limit(1).all()

            if not articles_to_analyze:
                print("✅ No hay artículos nuevos para analizar.")
                return
            
            print(f"📰 Encontrados {len(articles_to_analyze)} artículos para analizar")
            
            for article in articles_to_analyze:
                print(f"\n[{article.id}] Analizando: {article.title[:70]}...")
                
                try:
                    content = article.content or article.excerpt or ''
                    if len(content.strip()) < 50:
                        print("  ⚠️ Contenido insuficiente para análisis")
                        self.failed_articles += 1
                        continue
                    
                    entities = self.extract_entities(content)
                    analysis_result = self.analyze_article_with_gemini(article)
                    
                    if analysis_result:
                        if self.save_analysis_to_db(session, article.id, analysis_result, entities):
                            self.processed_articles += 1
                            print("  ✅ Análisis guardado correctamente")
                        else:
                            self.failed_articles += 1
                    else:
                        self.failed_articles += 1
                    
                    time.sleep(3)
                    
                except Exception as e:
                    error_msg = f"Error procesando artículo {article.id}: {e}"
                    print(f"  ❌ {error_msg}")
                    self.errors.append(error_msg)
                    self.failed_articles += 1
            
            print(f"\n{'='*50}\n🎉 ANÁLISIS COMPLETADO")
            print(f"✅ Artículos analizados exitosamente: {self.processed_articles}")
            print(f"❌ Artículos fallidos: {self.failed_articles}")
            if self.errors:
                print(f"\n⚠️ Errores encontrados ({len(self.errors)}):")
                for error in self.errors[:5]: print(f"  - {error}")
                if len(self.errors) > 5: print(f"  ... y {len(self.errors) - 5} errores más")

def generate_analysis_report():
     with app.app_context():
        session = db.session
        print("\n📊 Generando reporte de análisis...")
        total_articles = session.query(Article).count()
        analyzed_articles = session.query(Article).filter(Article.status == 'analyzed').count()
        
        print(f"\n=== REPORTE DE ANÁLISIS ===")
        print(f"📰 Total de artículos: {total_articles}")
        print(f"🤖 Artículos analizados: {analyzed_articles}")


def update_article_importance_scores():
    with app.app_context():
        session = db.session
        print("📊 Calculando scores de importancia...")
        articles_to_update = session.query(Article).filter(Article.status == 'analyzed').all()
        
        count = 0
        for article in articles_to_update:
            if article.analysis:
                analysis = article.analysis
                score = ( (analysis.local_relevance_score or 0) * 0.5 + 
                          (analysis.veracity_score or 0) * 0.3
                        ) / 100.0
                article.importance_score = score
                count += 1

        session.commit()
        print(f"  ✅ Scores de importancia actualizados para {count} artículos")

def main():
    try:
        analyzer = NewsAnalyzer()
        analyzer.run_analysis()
        
        if analyzer.processed_articles > 0:
            update_article_importance_scores()
        
        generate_analysis_report()
        
        print(f"\n{'='*60}\n🎉 PROCESO DE ANÁLISIS COMPLETADO")
        
    except KeyboardInterrupt:
        print("\nℹ️ Análisis interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico en el análisis: {e}")
        raise

if __name__ == "__main__":
    main()