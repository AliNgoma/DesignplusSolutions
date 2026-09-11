"""Uploaded image storage.

Locally (no SUPABASE_URL set) images are written to app/static/img/uploads,
same as before. In production the filesystem is read-only (Vercel functions),
so uploads go to a public Supabase Storage bucket instead and are served
straight from there.
"""
import mimetypes

import requests
from flask import current_app, url_for


def save_upload(file_storage, stored_name: str) -> None:
    if current_app.config['SUPABASE_URL']:
        _upload_to_supabase(file_storage, stored_name)
    else:
        file_storage.save(current_app.config['UPLOAD_DIR'] / stored_name)


def upload_url(filename: str) -> str:
    """Absolute URL for an uploaded image, wherever it's stored."""
    if not filename:
        return ''
    base = current_app.config['SUPABASE_URL']
    if base:
        bucket = current_app.config['SUPABASE_STORAGE_BUCKET']
        return f'{base}/storage/v1/object/public/{bucket}/{filename}'
    path = url_for('static', filename=f'img/uploads/{filename}')
    return f"{current_app.config['SITE_URL']}{path}"


def _upload_to_supabase(file_storage, stored_name: str) -> None:
    cfg = current_app.config
    bucket = cfg['SUPABASE_STORAGE_BUCKET']
    url = f"{cfg['SUPABASE_URL']}/storage/v1/object/{bucket}/{stored_name}"
    content_type = (file_storage.mimetype
                    or mimetypes.guess_type(stored_name)[0]
                    or 'application/octet-stream')
    resp = requests.post(
        url,
        headers={
            'Authorization': f"Bearer {cfg['SUPABASE_SERVICE_KEY']}",
            'Content-Type': content_type,
            'x-upsert': 'true',
        },
        data=file_storage.stream.read(),
        timeout=15,
    )
    resp.raise_for_status()
