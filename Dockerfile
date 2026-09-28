FROM python:3.14-slim@sha256:51dafde81dbdb6ebde285137a295cf18a47ca95234fe388a343719cb97305b3d

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py calculations.py constants.py models.py utils.py validation.py pdf_utils.py ./
COPY static/ static/
COPY templates/ templates/

# Unprivileged runtime user; app files stay root-owned and read-only.
# Port 8080 is above 1024 so no privileges are needed to bind it.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
USER app

ENV PORT=8080
EXPOSE 8080

# No curl in slim, so probe /health with urllib (PORT read from the environment).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request as u; u.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT','8080'), timeout=4)"

# Shell form so ${PORT} is expanded at runtime; hosts that inject PORT
# expect the app to bind to it.
#
# Default to a SINGLE worker so the default in-memory rate limiter is
# authoritative. To scale out, set WEB_CONCURRENCY>1 AND point
# RATELIMIT_STORAGE_URI at a shared backend (e.g. redis://) — otherwise rate
# limits become per-worker (see _warn_if_ratelimit_storage_unsafe in app.py).
#
# --threads 4 (>1 implies the gthread worker class) keeps one slow PDF export
# from blocking every other request while staying in a single process.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers "${WEB_CONCURRENCY:-1}" --threads 4 --timeout 120 --no-control-socket --access-logfile - app:app
