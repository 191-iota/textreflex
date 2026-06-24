FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway provides $PORT. Bind to it; the worker timeout must exceed AI_TIMEOUT
# (default 90s) so slow free-provider calls aren't killed mid-request.
ENV PORT=8080
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
