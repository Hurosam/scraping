# --- START OF FILE app/routes/api_routes.py ---

from flask import Blueprint, jsonify, request, send_file
import json
import unicodedata
from datetime import datetime, timedelta
import requests
import os
import hashlib
from urllib.parse import urlparse
from sqlalchemy import func, and_, or_

from ..extensions import db
from ..models import Article, NewsSource, Category, Location, ArticleAnalysis, Tag

api_bp = Blueprint('api', __name__)

IMAGE_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cache', 'images')
os.makedirs(IMAGE_CACHE_DIR, exist_ok=True)


@api_bp.route('/suggestions')
def api_suggestions():
    query = request.args.get('q', '').strip()
    if not query or len(query) < 3:
        return jsonify([])
    
    session = db.session
    try:
        search_term = f"%{query}%"
        suggestions = session.query(Article.title)\
            .filter(func.unaccent(func.lower(Article.title)).like(func.unaccent(func.lower(search_term))))\
            .order_by(Article.published_at.desc())\
            .limit(5).all()
        return jsonify([row[0] for row in suggestions])
    except Exception as e:
        print(f"Suggestions API Error: {e}")
        db.session.rollback()
        return jsonify([])


@api_bp.route('/filter_news')
def api_filter_news():
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 12, type=int)
        search_query = request.args.get('query', '').strip()
        category = request.args.get('category', '')
        source = request.args.get('source', '')
        province = request.args.get('province', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        sort_by = request.args.get('sortBy', 'published_at')
        show_all = request.args.get('show_all', 'false') == 'true'

        offset = (page - 1) * limit
        session = db.session

        # ✅ CORRECCIÓN: Query con select_from() explícito para evitar ambigüedad
        if not show_all:
            # Para show_all=false, necesitamos artículos CON análisis
            base_query = session.query(
                Article.id,
                Article.title,
                Article.link,
                Article.image_url,
                Article.published_at,
                Article.excerpt,
                NewsSource.display_name.label('source_name'),
                ArticleAnalysis.summary,
                ArticleAnalysis.veracity_score,
                ArticleAnalysis.local_relevance_score,
                ArticleAnalysis.civic_impact_score,
                Category.name.label('category_name'),
                Location.name.label('location_name')
            ).select_from(Article)\
             .join(NewsSource, Article.source_id == NewsSource.id)\
             .join(ArticleAnalysis, Article.id == ArticleAnalysis.article_id)\
             .outerjoin(Category, ArticleAnalysis.category_id == Category.id)\
             .outerjoin(Location, ArticleAnalysis.primary_location_id == Location.id)
        else:
            # Para show_all=true, incluimos artículos con y sin análisis
            base_query = session.query(
                Article.id,
                Article.title,
                Article.link,
                Article.image_url,
                Article.published_at,
                Article.excerpt,
                NewsSource.display_name.label('source_name'),
                ArticleAnalysis.summary,
                ArticleAnalysis.veracity_score,
                ArticleAnalysis.local_relevance_score,
                ArticleAnalysis.civic_impact_score,
                Category.name.label('category_name'),
                Location.name.label('location_name')
            ).select_from(Article)\
             .join(NewsSource, Article.source_id == NewsSource.id)\
             .outerjoin(ArticleAnalysis, Article.id == ArticleAnalysis.article_id)\
             .outerjoin(Category, ArticleAnalysis.category_id == Category.id)\
             .outerjoin(Location, ArticleAnalysis.primary_location_id == Location.id)

        # Aplicar filtros
        filters = []
        
        if search_query:
            search_term = f"%{search_query}%"
            filters.append(
                or_(
                    func.unaccent(func.lower(Article.title)).like(func.unaccent(func.lower(search_term))),
                    func.unaccent(func.lower(Article.excerpt)).like(func.unaccent(func.lower(search_term)))
                )
            )
        
        if category: filters.append(Category.name == category)
        if source: filters.append(NewsSource.name == source)
        if province: filters.append(Location.name == province)
        if start_date: filters.append(func.date(Article.published_at) >= start_date)
        if end_date: filters.append(func.date(Article.published_at) <= end_date)

        if filters:
            base_query = base_query.filter(and_(*filters))

        # Contar resultados totales
        count_query = session.query(func.count(Article.id)).select_from(Article)\
                             .join(NewsSource, Article.source_id == NewsSource.id)
        
        if not show_all:
            count_query = count_query.join(ArticleAnalysis, Article.id == ArticleAnalysis.article_id)
        else:
            count_query = count_query.outerjoin(ArticleAnalysis, Article.id == ArticleAnalysis.article_id)
            
        count_query = count_query.outerjoin(Category, ArticleAnalysis.category_id == Category.id)\
                                 .outerjoin(Location, ArticleAnalysis.primary_location_id == Location.id)
        
        if filters:
            count_query = count_query.filter(and_(*filters))
            
        total_results = count_query.scalar()

        # Ordenamiento
        order_map = {
            "published_at": Article.published_at.desc(),
            "veracity_score": ArticleAnalysis.veracity_score.desc(),
            "civic_impact_score": ArticleAnalysis.civic_impact_score.desc(),
            "local_relevance_score": ArticleAnalysis.local_relevance_score.desc(),
        }
        order_expression = order_map.get(sort_by, Article.published_at.desc())
        
        # Ejecutar query con paginación y ordenamiento
        query_results = base_query.order_by(order_expression).limit(limit).offset(offset).all()

        # Construir respuesta
        articles = []
        for row in query_results:
            articles.append({
                "id": row[0],  # Article.id
                "title": row[1],  # Article.title
                "link": row[2],  # Article.link
                "image_url": row[3],  # Article.image_url
                "published_at": row[4].isoformat() if row[4] else None,  # Article.published_at
                "excerpt": row[5],  # Article.excerpt
                "source_name": row[6],  # NewsSource.display_name
                "summary": row[7],  # ArticleAnalysis.summary
                "veracity_score": row[8],  # ArticleAnalysis.veracity_score
                "local_relevance_score": row[9],  # ArticleAnalysis.local_relevance_score
                "civic_impact_score": row[10],  # ArticleAnalysis.civic_impact_score
                "category_name": row[11],  # Category.name
                "location_name": row[12]  # Location.name
            })

        return jsonify({
            "articles": articles,
            "total_results": total_results,
            "current_page": page,
            "items_per_page": limit,
            "total_pages": (total_results + limit - 1) // limit if limit > 0 else 0
        })

    except Exception as e:
        print(f"Filter API Error: {e}")
        db.session.rollback()
        return jsonify(error=str(e)), 500
    
@api_bp.route('/dashboard_stats')
def api_dashboard_stats():
    # ✅ CAMBIO: Esta función ha sido completamente reescrita para usar SQLAlchemy
    try:
        start_date_str = request.args.get('start_date', '')
        end_date_str = request.args.get('end_date', '')
        source_name = request.args.get('source', '')
        show_all = request.args.get('show_all', 'false') == 'true'

        session = db.session
        
        base_query = session.query(Article).join(NewsSource)
        if not show_all:
            base_query = base_query.join(Article.analysis)

        filters = []
        if start_date_str: filters.append(func.date(Article.published_at) >= start_date_str)
        if end_date_str: filters.append(func.date(Article.published_at) <= end_date_str)
        if source_name: filters.append(NewsSource.name == source_name)
        
        if filters:
            base_query = base_query.filter(and_(*filters))

        date_range = session.query(func.min(func.date(Article.published_at)), func.max(func.date(Article.published_at))).first()
        total_articles = base_query.count()
        
        score_query = base_query.join(Article.analysis) if show_all else base_query
        avg_scores = score_query.with_entities(func.avg(ArticleAnalysis.veracity_score), func.avg(ArticleAnalysis.local_relevance_score), func.avg(ArticleAnalysis.civic_impact_score)).first()

        timeline_data = base_query.with_entities(func.date(Article.published_at).label('day'), func.count(Article.id).label('count')).group_by('day').order_by('day').all()
        
        category_query = base_query.join(Article.analysis).join(Category)
        categories_data = category_query.with_entities(Category.name, func.count(Article.id).label('count')).group_by(Category.name).order_by(func.count(Article.id).desc()).all()
        
        sources_data = base_query.with_entities(NewsSource.display_name, func.count(Article.id).label('count')).group_by(NewsSource.display_name).order_by(func.count(Article.id).desc()).all()

        location_query = base_query.join(Article.analysis).join(Location)
        top_locations = location_query.with_entities(Location.name, func.count(Article.id).label('count')).filter(Location.name != None).group_by(Location.name).order_by(func.count(Article.id).desc()).limit(5).all()

        tag_query = base_query.join(Article.tags)
        top_tags = tag_query.with_entities(Tag.name, func.count(Article.id).label('count')).group_by(Tag.name).order_by(func.count(Article.id).desc()).limit(5).all()

        stats = {
            "date_range": {"min_date": date_range[0], "max_date": date_range[1]},
            "total_articles": total_articles,
            "avg_scores": { "veracity": round(avg_scores[0] or 0, 1), "popular_interest": round(avg_scores[1] or 0, 1), "civic_impact": round(avg_scores[2] or 0, 1) },
            "timeline": [{"date": r.day, "count": r.count} for r in timeline_data],
            "categories": [{"name": r.name, "count": r.count} for r in categories_data],
            "sources": [{"name": r.display_name, "count": r.count} for r in sources_data],
            "top_locations": [{"name": r.name, "count": r.count} for r in top_locations],
            "top_tags": [{"name": r.name, "count": r.count} for r in top_tags]
        }
        return jsonify(stats)
    except Exception as e:
        print(f"Dashboard API Error: {e}")
        db.session.rollback()
        return jsonify(error=str(e)), 500

@api_bp.route('/filter_options')
def api_filter_options():
    session = db.session
    try:
        categories_query = session.query(Category.name).order_by(Category.name).all()
        sources_query = session.query(NewsSource.name, NewsSource.display_name).order_by(NewsSource.display_name).all()
        provinces_query = session.query(Location.name).filter_by(type='province').order_by(Location.name).all()

        filter_data = {
            "categories": [row[0] for row in categories_query],
            "sources": [{"value": row.name, "name": row.display_name} for row in sources_query],
            "provinces": [row[0] for row in provinces_query]
        }
        return jsonify(filter_data)
    except Exception as e:
        print(f"Filter Options API Error: {e}")
        return jsonify(error=str(e)), 500

def normalize_for_match(text: str) -> str:
    if not text: return ""
    nfkd_form = unicodedata.normalize('NFD', text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return only_ascii.upper()


@api_bp.route('/map_geojson')
def api_map_geojson():
    # ✅ CAMBIO: Esta función ha sido reescrita para usar SQLAlchemy
    session = db.session
    try:
        location_counts_query = session.query(Location.name, func.count(Article.id).label('count'))\
            .join(ArticleAnalysis, ArticleAnalysis.primary_location_id == Location.id)\
            .join(Article)\
            .group_by(Location.name).all()
        
        counts_dict = {normalize_for_match(row.name): row.count for row in location_counts_query}

        try:
            with open('geojson/huanuco_provinces.json', 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
        except FileNotFoundError:
            return jsonify({"error": "GeoJSON data file not found on server."}), 404

        for feature in geojson_data['features']:
            province_name = normalize_for_match(feature['properties'].get('NAME', ''))
            count = counts_dict.get(province_name, 0)
            feature['properties']['NOTICIAS_COUNT'] = count
            
        return jsonify(geojson_data)
        
    except Exception as e:
        print(f"GeoJSON API Error: {e}")
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {e}"}), 500

@api_bp.route('/image_proxy')
def image_proxy():
    external_url = request.args.get('url')
    if not external_url:
        return "URL de imagen no proporcionada.", 400

    try:
        url_hash = hashlib.sha256(external_url.encode('utf-8')).hexdigest()
        path = urlparse(external_url).path
        ext = os.path.splitext(path)[1] or '.jpg'

        cached_filename = f"{url_hash}{ext}"
        cached_filepath = os.path.join(IMAGE_CACHE_DIR, cached_filename)

        if os.path.exists(cached_filepath):
            return send_file(cached_filepath)

        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(external_url, headers=headers, stream=True, timeout=20)
        response.raise_for_status()
        
        with open(cached_filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return send_file(cached_filepath)

    except requests.exceptions.RequestException as e:
        print(f"Error en Proxy de Imagen (descarga): {e}")
        return "No se pudo obtener la imagen del servidor externo.", 502
    except Exception as e:
        print(f"Error en Proxy de Imagen (general): {e}")
        return "Error interno al procesar la imagen.", 500