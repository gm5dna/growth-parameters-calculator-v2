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
CMD exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 2 --timeout 120 --access-logfile - app:app
