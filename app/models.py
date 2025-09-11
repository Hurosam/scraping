# --- START OF FILE app/models.py ---

from .extensions import db, bcrypt
from flask_login import UserMixin
from datetime import datetime

# --- Tablas de Asociación ---

# Puente entre usuarios y roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True)
)

# Puente entre artículos y tags
article_tags = db.Table('article_tags',
    db.Column('article_id', db.Integer, db.ForeignKey('articles.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# --- Modelos de Autenticación y Usuarios ---

class User(UserMixin, db.Model):
    """Modelo de Usuario."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
                            backref=db.backref('users', lazy=True))

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

    def __repr__(self):
        return f'<User {self.email}>'

class Role(db.Model):
    """Modelo de Roles."""
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def __repr__(self):
        return f'<Role {self.name}>'


# --- Modelos de Contenido de Noticias ---

class NewsSource(db.Model):
    """Modelo para las fuentes de noticias (ej: Diario Correo)."""
    __tablename__ = 'news_sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # ej: 'diario_correo'
    display_name = db.Column(db.String(100), unique=True, nullable=False) # ej: 'Diario Correo'
    articles = db.relationship('Article', backref='source', lazy=True)

    def __repr__(self):
        return f'<NewsSource {self.display_name}>'

class Category(db.Model):
    """Modelo para las categorías de noticias (ej: Política, Deporte)."""
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f'<Category {self.name}>'

class Location(db.Model):
    """Modelo para las ubicaciones geográficas."""
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    db.UniqueConstraint('name', 'type', name='uq_location_name_type')

    def __repr__(self):
        return f'<Location {self.name} ({self.type})>'

class Tag(db.Model):
    """Modelo para los tags o palabras clave."""
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    usage_count = db.Column(db.Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<Tag {self.name}>'

class Article(db.Model):
    """Modelo principal para cada noticia."""
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    link = db.Column(db.String(512), unique=True, nullable=False, index=True)
    source_id = db.Column(db.Integer, db.ForeignKey('news_sources.id'), nullable=False)
    status = db.Column(db.String(50), default='scraped', nullable=False, index=True)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text)
    image_url = db.Column(db.String(512))
    published_at = db.Column(db.DateTime, index=True)
    scraped_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    importance_score = db.Column(db.Float, default=0.0, nullable=False)
    
    analysis = db.relationship('ArticleAnalysis', backref='article', uselist=False, cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary=article_tags, lazy='subquery',
                           backref=db.backref('articles', lazy=True))
                           
    def __repr__(self):
        return f'<Article {self.id}: {self.title[:50]}>'

class ArticleAnalysis(db.Model):
    """Modelo para almacenar los resultados del análisis de IA."""
    __tablename__ = 'article_analysis'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), unique=True, nullable=False)
    summary = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    primary_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'))
    veracity_score = db.Column(db.Integer)
    civic_impact_score = db.Column(db.Integer)
    local_relevance_score = db.Column(db.Integer)
    # ... aquí podrías añadir más campos si el análisis de IA se vuelve más complejo.

    def __repr__(self):
        return f'<ArticleAnalysis for Article {self.article_id}>'