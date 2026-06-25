# ---------------------------------------------------------------------------
# Image backend Smart Campus
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# Bonnes pratiques Python en conteneur.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dépendances système minimales (psycopg/cryptography/reportlab utilisent des
# wheels précompilées ; netcat sert au healthcheck de l'entrypoint).
RUN apt-get update \
    && apt-get install -y --no-install-recommends netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Couche dépendances (cache Docker tant que requirements ne change pas).
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Code applicatif.
COPY . .

# Entrypoint : attend la base, migre, (seed optionnel) puis lance la commande.
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
