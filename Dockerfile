FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py calculations.py constants.py models.py utils.py validation.py pdf_utils.py ./
COPY static/ static/
COPY templates/ templates/

ENV PORT=8080
EXPOSE 8080

# Shell form so ${PORT} is expanded at runtime; hosts like Render.com inject
# a dynamic PORT and expect the app to bind to it.
#
# Default to a SINGLE worker so the default in-memory rate limiter is
# authoritative. To scale out, set WEB_CONCURRENCY>1 AND point
# RATELIMIT_STORAGE_URI at a shared backend (e.g. redis://) — otherwise rate
# limits become per-worker (see _warn_if_ratelimit_storage_unsafe in app.py).
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers "${WEB_CONCURRENCY:-1}" --timeout 120 --access-logfile - app:app
