web: gunicorn wsgi:app --workers 2 --threads 4 --timeout 60
release: flask --app wsgi init-db && flask --app wsgi seed
