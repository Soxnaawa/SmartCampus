#!/bin/sh
# ---------------------------------------------------------------------------
# Entrypoint conteneur : attend PostgreSQL, applique les migrations puis lance
# la commande passée (serveur web ou listener MQTT).
# ---------------------------------------------------------------------------
set -e

# Attendre que PostgreSQL réponde (si DB_HOST est défini).
if [ -n "$DB_HOST" ]; then
  echo "Attente de PostgreSQL sur $DB_HOST:${DB_PORT:-5432}…"
  while ! nc -z "$DB_HOST" "${DB_PORT:-5432}"; do
    sleep 0.5
  done
  echo "PostgreSQL est prêt."
fi

# Migrations (idempotentes).
python manage.py migrate --noinput

# Seed automatique optionnel : SEED_ON_START=1 dans l'environnement.
if [ "$SEED_ON_START" = "1" ]; then
  echo "Génération des données de test (seed_data)…"
  python manage.py seed_data || true
fi

# Collecte des statiques en production (ignorée si DEBUG).
python manage.py collectstatic --noinput >/dev/null 2>&1 || true

exec "$@"
