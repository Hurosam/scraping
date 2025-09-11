# --- START OF FILE app/routes/main_routes.py ---

from flask import Blueprint, render_template, request
import json
from urllib.parse import quote
from sqlalchemy.orm import joinedload, subqueryload

# Importamos los modelos y la sesión de db
from ..extensions import db
from ..models import Article, ArticleAnalysis, Category, Location

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/noticia/<int:article_id>')
def noticia_detalle(article_id):
    session = db.session
    try:
        # ✅ CORRECCIÓN: Query simple del artículo con sus relaciones básicas
        article = session.query(Article)\
                         .options(
                             joinedload(Article.source),
                             subqueryload(Article.tags)
                         ).filter(Article.id == article_id).first()

        if not article:
            return render_template('error.html', error_message="Noticia no encontrada", error_code=404), 404

        # Obtener análisis, categoría y ubicación por separado
        analysis = session.query(ArticleAnalysis).filter_by(article_id=article_id).first()
        
        category_name = None
        location_name = None
        
        if analysis:
            if analysis.category_id:
                category = session.query(Category).filter_by(id=analysis.category_id).first()
                category_name = category.name if category else None
                
            if analysis.primary_location_id:
                location = session.query(Location).filter_by(id=analysis.primary_location_id).first()
                location_name = location.name if location else None

        # Construir diccionario del artículo con manejo seguro de fechas
        article_dict = {
            "id": article.id,
            "title": article.title,
            "link": article.link,
            "image_url": article.image_url,
            "published_at": article.published_at.isoformat() if article.published_at else None,
            "scraped_at": article.scraped_at.isoformat() if article.scraped_at else None,
            "excerpt": article.excerpt,
            "content": article.content,
            "source_name": article.source.display_name if article.source else "Fuente desconocida",
            "tags_list": [tag.name for tag in article.tags] if article.tags else []
        }
        
        # Agregar datos de análisis si existen
        if analysis:
            article_dict.update({
                "summary": analysis.summary,
                "veracity_score": analysis.veracity_score,
                "local_relevance_score": analysis.local_relevance_score,
                "civic_impact_score": analysis.civic_impact_score,
                "category_name": category_name or "Sin categoría",
                "location_name": location_name or "Ubicación no especificada"
            })
        else:
            # Valores por defecto si no hay análisis
            article_dict.update({
                "summary": None,
                "veracity_score": None,
                "local_relevance_score": None,
                "civic_impact_score": None,
                "category_name": "Sin categoría",
                "location_name": "Ubicación no especificada"
            })
        
        # Procesamiento de URL de imagen
        image_url = article_dict.get('image_url')
        if image_url and image_url.startswith('http'):
            article_dict['image_url'] = f"/api/image_proxy?url={quote(image_url)}"

        # Campos adicionales que la plantilla podría esperar
        article_dict['people_mentioned_list'] = []
        article_dict['organizations_mentioned_list'] = []
        article_dict['mentioned_locations_list'] = []
        
        return render_template('detalle_noticia.html', article=article_dict)
    
    except Exception as e:
        print(f"Error en noticia_detalle para ID {article_id}: {e}")
        db.session.rollback()
        return render_template('error.html', error_message=f"Error de base de datos", error_code=500), 500

@main_bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@main_bp.route('/mapa')
def mapa():
    return render_template('mapa.html')