#!/bin/bash
# Construye scribetracker_azure.zip para subirlo a App Service (Linux, Python 3.12).
# Incluye: backend (sin tests ni instance), dependencias ya compiladas para Linux
# en paquetes/, el build de Angular en frontend_dist/ y startup.sh.
# Uso (en Linux):  bash despliegue/azure/construir_paquete.sh <carpeta_salida>
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
SALIDA="${1:-$RAIZ/despliegue/azure/salida}"
TMP="$(mktemp -d)"
echo "1/4 Angular"
(cd "$RAIZ/frontend" && npx ng build >/dev/null)
echo "2/4 Código del backend"
mkdir -p "$TMP/pkg"
cp -r "$RAIZ/backend/app" "$RAIZ/backend/migrations" "$RAIZ/backend/config.py" "$RAIZ/backend/wsgi.py" "$TMP/pkg/"
find "$TMP/pkg" -name "__pycache__" -type d -prune -exec rm -rf {} +
cp "$RAIZ/despliegue/azure/startup.sh" "$TMP/pkg/"
cp -r "$RAIZ/frontend/dist/frontend/browser" "$TMP/pkg/frontend_dist"
echo "3/4 Dependencias para Linux (Python 3.12)"
grep -v -i "^waitress" "$RAIZ/backend/requirements.txt" > "$TMP/req.txt"
echo "gunicorn==23.0.0" >> "$TMP/req.txt"
# Paquetes que solo se publican como código fuente (puro Python): se convierten a wheel aquí.
python3 -m pip wheel -q --no-deps -w "$TMP/ruedas" http-ece py-vapid
python3 -m pip install -q --target "$TMP/pkg/paquetes" --find-links "$TMP/ruedas" --platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64 \
  --implementation cp --python-version 3.12 --only-binary=:all: -r "$TMP/req.txt"
# Si Azure compila el paquete al subirlo (Oryx, p. ej. desde Kudu "Deployments"),
# instala estas dependencias en su entorno virtual "antenv" con este archivo.
cp "$TMP/req.txt" "$TMP/pkg/requirements.txt"
echo "4/4 Zip"
mkdir -p "$SALIDA"
rm -f "$SALIDA/scribetracker_azure.zip"
(cd "$TMP/pkg" && zip -qr "$SALIDA/scribetracker_azure.zip" .)
rm -rf "$TMP"
ls -lh "$SALIDA/scribetracker_azure.zip"
