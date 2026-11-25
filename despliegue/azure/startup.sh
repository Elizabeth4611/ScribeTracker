#!/bin/bash
# ============================================================
#  Arranque de ScribeTracker en Azure App Service (Linux, Python 3.12)
#  Comando de inicio en el portal:  bash startup.sh
#  (ruta relativa: si Azure "compila" el paquete al subirlo desde Kudu, lo
#  descomprime en /tmp/<algo> y ejecuta el comando desde esa carpeta).
# ============================================================
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"
echo "[startup] Carpeta de la aplicación: $APP_DIR"
export PYTHONPATH="$APP_DIR/paquetes:${PYTHONPATH}"

# 1) Controlador ODBC de SQL Server. La imagen de Python de App Service no
#    siempre lo trae y lo que se instala a mano se pierde al reiniciar, así que
#    se revisa en cada arranque (si falta, tarda ~1 min en instalarse).
if ! odbcinst -q -d 2>/dev/null | grep -q "ODBC Driver 18 for SQL Server"; then
  echo "[startup] Instalando ODBC Driver 18 for SQL Server..."
  . /etc/os-release
  curl -sSL "https://packages.microsoft.com/config/debian/${VERSION_ID%%.*}/packages-microsoft-prod.deb" -o /tmp/msprod.deb \
    && dpkg -i /tmp/msprod.deb >/dev/null \
    && apt-get update -qq \
    && ACCEPT_EULA=Y apt-get install -y -qq msodbcsql18 unixodbc >/dev/null \
    && echo "[startup] ODBC instalado." \
    || echo "[startup] ERROR: no se pudo instalar el controlador ODBC."
fi

# 2) Carpetas que deben sobrevivir a cada publicación (fuera de wwwroot).
mkdir -p /home/datos "${EVIDENCIAS_DIR:-/home/datos/evidencias}" "${VAPID_DIR:-/home/datos}"
export EVIDENCIAS_DIR="${EVIDENCIAS_DIR:-/home/datos/evidencias}"
export VAPID_DIR="${VAPID_DIR:-/home/datos}"

# 3) Clave secreta de las sesiones: si no se configuró en el portal, se genera una
#    sola vez y se guarda en /home/datos (nunca en el código ni en el chat).
if [ -z "${SECRET_KEY:-}" ]; then
  if [ ! -s /home/datos/secret_key ]; then
    python -c "import secrets; print(secrets.token_hex(32))" > /home/datos/secret_key
    chmod 600 /home/datos/secret_key
  fi
  export SECRET_KEY="$(cat /home/datos/secret_key)"
fi
export FRONTEND_DIST="$APP_DIR/frontend_dist"
export SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-true}"

# 4) Servidor de producción.
exec python -m gunicorn --bind "0.0.0.0:${PORT:-8000}" --workers 2 --threads 8 \
     --timeout 120 --access-logfile - --error-logfile - wsgi:app
