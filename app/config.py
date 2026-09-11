"""Configuration, read from the environment with sane local defaults."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def _database_uri() -> str:
    """Postgres in production, SQLite locally.

    Render (and most managed hosts) hand out `postgres://` URLs, which
    SQLAlchemy 2 no longer recognises — it wants an explicit driver.
    """
    url = os.environ.get('DATABASE_URL')
    if not url:
        return f"sqlite:///{BASE_DIR / 'instance' / 'designplus.sqlite3'}"
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url


def _engine_options(uri: str) -> dict:
    """Tuned small on serverless: one function invocation needs at most a
    couple of connections, and behind Supabase's pooler (Supavisor/PgBouncer
    in transaction mode) server-side prepared statements aren't safe to
    reuse across requests, so they're disabled for Postgres.
    """
    options = {'pool_pre_ping': True, 'pool_size': 3, 'max_overflow': 2}
    if uri.startswith('postgresql'):
        options['connect_args'] = {'prepare_threshold': None}
    return options


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-insecure-key')
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(SQLALCHEMY_DATABASE_URI)

    # Set to use Supabase Storage for uploads (required in production, since
    # Vercel's filesystem is read-only outside of /tmp). Left unset locally
    # to keep writing straight to app/static/img/uploads.
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
    SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'uploads')

    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000').rstrip('/')

    # Uploaded project and client images.
    UPLOAD_DIR = BASE_DIR / 'app' / 'static' / 'img' / 'uploads'
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif'}

    # Session cookies: hardened, but not `Secure` on plain-HTTP localhost.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SITE_URL', '').startswith('https://')

    SMTP_HOST = os.environ.get('SMTP_HOST')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    NOTIFY_EMAIL = os.environ.get('NOTIFY_EMAIL')

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@designplussolutions.co.ke')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')
