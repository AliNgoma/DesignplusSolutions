"""WSGI entry point.

Local:       flask --app wsgi run --debug
Production:  gunicorn wsgi:app
"""
from app import create_app

app = create_app()
