# ScribeTracker

Monitoreo de jornadas de promotoría para Scribe (Bio Pappel).
- **Backend:** Python 3.13, Flask, SQLAlchemy y SQL Server.
- **Frontend:** Angular 21, con vista móvil del promotor y panel web de supervisión y administración.

- Estado actual y siguiente paso: [`docs/ESTADO_PROYECTO.md`](docs/ESTADO_PROYECTO.md)
- Requisitos, decisiones y límites: [`docs/MATRIZ_REQUISITOS.md`](docs/MATRIZ_REQUISITOS.md)
- Registro de pruebas para la docente: [`docs/pruebas/`](docs/pruebas/)
- **Reporte de pruebas con imágenes:** [`docs/REPORTE_PRUEBAS.md`](docs/REPORTE_PRUEBAS.md) (evidencias en `docs/evidencias/`)

## Instalación (Windows, primera vez)

Requisitos: Python 3.13, Node.js 20.19+, 22.12+ o 24+, SQL Server con ODBC Driver 18 y autenticación de Windows.

1. `backend\.env` (no se sube a Git) con `DB_SERVER`, `DB_NAME`, `DB_DRIVER` y `SECRET_KEY`. Usa `backend\.env.example` como guía.
2. Abre `scripts\etapa2_bd.bat` con doble clic. Este script:
   - instala las dependencias de Python (incluido reportlab para los PDF);
   - **respalda** la base de datos;
   - aplica las migraciones;
   - crea la base separada `ScribeTracker_Pruebas` y corre las pruebas.

   Resultado en `scripts\logs\etapa2_bd.log`.
3. Abre `scripts\construir_frontend.bat`. Instala las dependencias de Angular (incluido Leaflet para los mapas) y compila. Resultado en `scripts\logs\frontend.log`.

Para migrar a mano: en `backend`, `.venv\Scripts\activate` y `flask --app app db upgrade`.

## Ejecución

Abre `scripts\iniciar.bat`. Detiene las instancias anteriores y abre dos ventanas: Flask en `http://127.0.0.1:5000` y Angular en `http://localhost:4200`. Abre **http://localhost:4200** en Chrome.

## Demostración

1. `scripts\crear_usuarios_prueba.bat` crea usuarios de prueba (una vez). Sus contraseñas quedan en `scripts\logs\usuarios_prueba.txt`.
2. `scripts\datos_demo.bat` crea 4 tiendas en León y asigna las tiendas de **hoy** al promotor de prueba. Vuelve a ejecutarlo cada día de demostración. Las coordenadas quedan en `scripts\logs\datos_demo.log`.
3. **Simular la ubicación**, porque la laptop no está en las tiendas: en Chrome, `F12` → menú ⋮ → *More tools* → **Sensors** → *Location* → *Other…* y escribe la latitud y longitud de la tienda.
   - Para iniciar la jornada usa la primera tienda (Walmart Torres Landa: 21.1458, -101.6893).
   - Para probar el rechazo, usa otra tienda o coordenadas a más de 100 m.
4. **Cámara:** Chrome pide permiso. La cámara y la ubicación solo funcionan en `http://localhost` o con HTTPS. Para usar el celular por red local se necesita HTTPS (`ng serve --ssl`).
5. Recorrido del promotor:
   1. Entra como `promotor.prueba@…` y ve a **Entrada/salida**.
   2. INICIAR JORNADA.
   3. CHECK-IN.
   4. TOMAR FOTOS: las 4 categorías.
   5. CHECK-OUT.
   6. Pausas.
   7. FINALIZAR JORNADA.
6. Recorrido del supervisor: entra como `supervisor.prueba@…` y revisa el Módulo de supervisión (mapa y alertas), Rutas del día, Gestión de rutas, Incidencias y Reportes (PDF).
7. Recorrido del administrador: entra como `admin.prueba@…` y revisa Usuarios, Tiendas, Rutas, Parámetros y Reportes.
8. Modo sin conexión: con DevTools → *Network* → **Offline**, haz check-in o toma fotos. Aparecen como "pendientes de sincronizar"; al volver a *Online* se envían y el servidor las valida.

## Pruebas

- `scripts\pruebas.bat` corre todas las pruebas del backend contra SQL Server (base `ScribeTracker_Pruebas`) y contra SQLite. Deja los XML en `docs\pruebas\` y la salida en `scripts\logs\pruebas.log`.
- A mano: en `backend`, `python -m pytest -v`. Usa SQLite; para usar SQL Server, define antes `set ST_BD_PRUEBAS=ScribeTracker_Pruebas`.
- Registro para la docente: `python scripts\generar_registro_pruebas.py` genera `docs\pruebas\REGISTRO_PRUEBAS.md` y `registro_pruebas.csv`.
- Evidencias con SQL Server: `scripts\evidencias_sqlserver_interfaz.bat` (base `ScribeTracker_Pruebas`, nunca la real) guarda el detalle HTTP de cada caso, las capturas de la interfaz en `docs\evidencias\sqlserver\` y el caso F08. Después: `python scripts\evidencias\generar_reporte.py` y `python scripts\evidencias\verificar_evidencias.py`.
- Antes de subir a GitHub: `scripts\copiar_a_github.bat` (copia sin `.env`, respaldos ni logs y revisa secretos).

## API principal

| Ruta | Rol |
|---|---|
| `/api/auth/login`, `/logout`, `/me`, `/cambiar-password` | Todos |
| `/api/usuarios`, `/api/parametros`, `/api/tiendas` (escritura) | Administrador |
| `/api/rutas`, `/api/asignaciones`, `/api/supervision/*`, `/api/incidencias`, `/api/reportes` | Supervisor (sus promotores) y Administrador |
| `/api/promotor/hoy`, `/jornada/*`, `/visitas/*`, `/evidencias`, `/pausas/*`, `/ubicaciones`, `/historial` | Promotor (solo sus registros) |
