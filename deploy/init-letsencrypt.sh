#!/usr/bin/env bash
# Bootstrap TLS for the Beezents production stack on AWS EC2.
#
# Generates deploy/nginx.conf from deploy/nginx.conf.template, creates a
# temporary self-signed certificate so nginx can boot, then requests a real
# Let's Encrypt certificate via the HTTP-01 challenge.
#
# Usage (run from the repository root on the EC2 instance):
#   DOMAIN=api.beezents.com EMAIL=admin@beezents.com ./deploy/init-letsencrypt.sh
#
# Optional: STAGING=1 to test against Let's Encrypt's staging API (avoids
# hitting the rate limit while testing).
set -euo pipefail

DOMAIN="${DOMAIN:?Set DOMAIN (e.g. api.beezents.com) when running this script}"
EMAIL="${EMAIL:-}"
STAGING="${STAGING:-0}"

cd "$(dirname "$0")/.."

if [ ! -f .env.production ]; then
    echo "[init] Missing .env.production — copy .env.production.example and fill in real values first."
    exit 1
fi

# Generate the nginx site config from the template.
sed -e "s/__DOMAIN__/${DOMAIN}/g" deploy/nginx.conf.template > deploy/nginx.conf
echo "[init] Wrote deploy/nginx.conf for ${DOMAIN}"

# 1. Create a dummy certificate so nginx can start with the full TLS config
#    before the real Let's Encrypt certificate exists.
echo "[init] Creating dummy certificate..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/${DOMAIN}/privkey.pem \
    -out /etc/letsencrypt/live/${DOMAIN}/fullchain.pem \
    -subj /CN=localhost" certbot

# 2. Start nginx so the ACME challenge path is reachable.
echo "[init] Starting nginx..."
docker compose -f docker-compose.prod.yml up -d --force-recreate nginx

# 3. Remove the dummy certificate.
echo "[init] Removing dummy certificate..."
docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/${DOMAIN} \
          /etc/letsencrypt/archive/${DOMAIN} \
          /etc/letsencrypt/renewal/${DOMAIN}.conf" certbot

# 4. Request the real certificate.
echo "[init] Requesting Let's Encrypt certificate for ${DOMAIN}..."
STAGING_ARG=""
if [ "${STAGING}" = "1" ]; then
    STAGING_ARG="--staging"
fi
EMAIL_ARG=""
if [ -n "${EMAIL}" ]; then
    EMAIL_ARG="--email ${EMAIL}"
else
    EMAIL_ARG="--register-unsafely-without-email"
fi

docker compose -f docker-compose.prod.yml run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    ${STAGING_ARG} \
    ${EMAIL_ARG} \
    -d ${DOMAIN} \
    --rsa-key-size 2048 \
    --agree-tos \
    --force-renewal" certbot

# 5. Reload nginx so it serves the real certificate.
echo "[init] Reloading nginx..."
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

echo "[init] Done. Start the full stack with:"
echo "  docker compose -f docker-compose.prod.yml up -d --build"