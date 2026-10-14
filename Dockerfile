FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

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
# authoritative. Multi-worker needs RATELIMIT_STORAGE_URI=redis://.
#
# --threads 4 (>1 implies the gthread worker class) keeps one slow PDF export
# from blocking every other request while staying in a single process.
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers "${WEB_CONCURRENCY:-1}" --threads 4 --timeout 120 --no-control-socket --access-logfile - app:app
