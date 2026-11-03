# Estado del proyecto · ScribeTracker

Última actualización: **3 de noviembre de 2026, 16:05** (entrega: miércoles 4 de noviembre).

## Carpetas

- **Carpeta de trabajo y ejecución: `C:\ScribeTracker`.** Aquí están `backend\.env`, el entorno virtual `.venv`, `node_modules` y la base real de SQL Server. Todo el desarrollo se hizo aquí.
- Su Git **no está vinculado** a GitHub: el remoto es el texto de ejemplo `https://github.com/TU_USUARIO/ScribeTracker.git` y el historial (`721de2c`) es distinto del de GitHub. **No hay commit** de esta etapa.
- `C:\Users\eeliz\Documents\GitHub\ScribeTracker` es la copia vinculada a GitHub (`Elizabeth4611/ScribeTracker`), con solo los commits iniciales y la etapa 1 sin confirmar. **No se usó** en esta etapa.
- **Decisión pendiente:** cómo unificar las copias. Opción sugerida: en `C:\ScribeTracker`, cambiar el remoto a `Elizabeth4611/ScribeTracker`, hacer commit y subir a una rama nueva (`etapa-2`) para revisarla antes de unirla a `main`.

## Terminado y comprobado

| Módulo | Base de datos | Backend | Frontend | Pruebas |
|---|---|---|---|---|
| Acceso y usuarios | Columnas nuevas en Usuario (número de empleado, intentos, contraseña temporal, baja) | CRUD, baja lógica, contraseña temporal, cambio obligatorio, alcance por rol | Login, recuperar, cambiar contraseña, Gestión de usuarios | U01-U12, AUT |
| Parámetros globales | Tabla Parametro (15 parámetros) | Consultar, editar, restablecer | Pantalla de parámetros | U12 |
| Tiendas | Tabla Tienda | Alta, edición, filtros, baja lógica protegida | Gestión de tiendas con mapa | T01-T06 |
| Rutas y asignaciones | Ruta, Ruta_Tienda, Asignacion (historial) | Plantillas, aplicar a fechas, asignación por día | Rutas, Gestión de rutas | R01-R06 |
| Jornada, visitas, evidencias, pausas | Jornada, Visita, Evidencia, Pausa, Ubicacion | Reglas C1-C9 y D en el servidor | Vista móvil del promotor completa | J, V, E, P, A; E2E-01…06 |
| Seguimiento e incidencias | Incidencia | Estados separados, alertas internas, seguimiento manual | Mapa de supervisión, Rutas del día, Incidencias | S01-S03, I01-I03, E2E-08 |
| Reportes | Reporte | Diario, semanal y mensual; Desempeño, Incidencias, Exhibición; PDF | Reportes | REP01-REP04, E2E-09 |
| Sin conexión | Evento_Cliente (idempotencia) | X-Id-Cliente, hora de captura, origen | Cola IndexedDB, pendientes y confirmados; la pantalla se actualiza al sincronizar (F08) | O01-O04, E2E-07, CP-28 |

- **Migración** `c87399dedb00` aplicada en la base real `ScribeTracker`, con **respaldo previo** en `C:\Program Files\Microsoft SQL Server\MSSQL17.SQLEXPRESS02\MSSQL\Backup\ScribeTracker_antes_etapa2_20261102_225908.bak`. Había 5 usuarios antes y siguen los 5 después.
- **Base de pruebas separada** `ScribeTracker_Pruebas` creada en el mismo SQL Server. La migración se probó también sobre esa base vacía.
- **Frontend:** compilado en producción sin errores (`npm run build`); revisión estricta de plantillas (`ngc`) sin errores.

## Pruebas realizadas (ejecuciones reales)

| Fecha y hora | Entorno | Resultado |
|---|---|---|
| 02/11 22:30-22:50 | Desarrollo (Linux, SQLite) | Se detectaron y corrigieron F01-F06. Final: 91 de 91 |
| 02/11 22:59-23:04 | **Laptop · SQL Server** (`ScribeTracker_Pruebas`) | **91 passed** en 4 min 56 s (`scripts/logs/etapa2_bd.log`) |
| 02/11 23:04 | Laptop · SQLite | 91 passed |
| 02/11 23:20-23:26 | **Laptop · navegador + Flask + SQL Server real** | E2E-01…09 exitosas; E2E-07 encontró el defecto F07, corregido y verificado |
| 02/11 23:26-23:31 | **Laptop · SQL Server + SQLite** (`scripts/pruebas.bat`) | **91 passed** en SQL Server (4 min 29 s) y **91 passed** en SQLite; registro generado |
| 03/11 14:56-15:05 | **Laptop · SQL Server** (`scripts/evidencias_sqlserver.bat`) | Casos CP-01…06 y CP-08…27, uno por uno: los 26 con código de salida 0 |
| 03/11 15:14-15:19 | Desarrollo · Angular (build de producción) + Flask + SQLite | **Fallo nuevo F08** (CP-28): tras sincronizar, la pantalla no reflejaba el servidor. Corregido, recompilado en la laptop (15:17) y verificado con el mismo caso |
| 03/11 15:20-15:25 | Desarrollo · Angular + Flask + SQLite | Capturas UI-01…UI-27 y CP-07 repetido; detalle HTTP obtenido de cada caso |
| 03/11 15:45-15:49 | **Laptop · SQL Server** (`ScribeTracker_Pruebas`) | Casos del reporte en una sola sesión: **34 passed** con el detalle HTTP obtenido (`docs/evidencias/salidas/obtenidos_sqlserver.xml`) |
| 03/11 15:50-15:52 | **Laptop · Angular (build 15:17) + Flask + SQL Server** (`ScribeTracker_Pruebas`) | 29 capturas de pantalla reales en `docs/evidencias/sqlserver/` (incluye las 4 pendientes: UI-05, UI-07, UI-15, UI-18 y el PDF) |
| 03/11 15:52 | **Laptop · Angular + Flask + SQL Server** | **F08 verificado con SQL Server** (CP-28): 5 s después de recuperar la señal, la pantalla muestra Soriana "En curso" y sin CHECK-IN, igual que el servidor |

Todo lo de la laptop con SQL Server del 03/11 15:45 se hizo con `scripts\evidencias_sqlserver_interfaz.bat` (registro en `scripts\logs\sqlserver_interfaz.log`, resumen `pytest=0 interfaz=0 cp28=0`). Usa solo la base de pruebas: el servidor de capturas se niega a usar una base que no termine en `_Pruebas` o que sea la de `DB_NAME`.

Fallos reales y correcciones: F01-F08 en `docs/pruebas/historial_fallos.json`; registros de texto originales de F01-F07 en `docs/pruebas/evidencias/`.

## Reporte de pruebas con imágenes (para la docente)

- **`docs/REPORTE_PRUEBAS.md`**: 28 casos con requisito, tipo de resultado (defecto, error de la prueba, rechazo esperado o flujo válido), datos, procedimiento, código, esperado, obtenido, estado, entorno e imágenes. Los 8 fallos tienen imagen antes y después, causa, archivo y fragmentos corregidos.
- **`docs/evidencias/`**: 95 imágenes citadas en el reporte: **35 generadas a partir de registros de texto** (📄, no son capturas), **58 capturas de pantalla reales** (🖥️: 29 de desarrollo con SQLite y 29 + CP-28 de la laptop con SQL Server en `sqlserver/`) y 2 páginas de PDF. La sección 8 del reporte es el inventario con el origen de cada una. `salidas/` guarda los textos originales.
- Comprobación: `python scripts\evidencias\verificar_evidencias.py` abre cada imagen citada.
- Se regenera con `python scripts\evidencias\generar_reporte.py`.
- **Límites declarados en el reporte:** las imágenes "antes" de F01-F07 son los registros de texto originales convertidos a imagen (no había capturas); las de resultado del backend son la salida de pytest en SQL Server convertida a imagen; E2E-01…09 y la verificación original de F07 (02/11) solo tienen registro de texto. Las capturas de SQLite se conservan junto a las de SQL Server. En UI-05 con SQL Server el mapa base no terminó de cargar (los datos sí).
- Los usuarios de demostración de las capturas ya no tienen contraseña escrita en el código: el orquestador genera una aleatoria en cada ejecución (variable `ST_DEMO_PASSWORD`).

## Lo que falta actualizar (siguiente paso)

1. ~~Registro de pruebas~~, ~~reporte con imágenes~~, ~~detalle HTTP con SQL Server~~, ~~capturas con SQL Server~~ y ~~F08 con SQL Server~~: HECHO.
2. **Respaldar en GitHub** (todavía no hay commit de la etapa 2): `scripts\copiar_a_github.bat` copia a `Documents\GitHub\ScribeTracker` sin `.env`, respaldos, logs ni dependencias y revisa secretos con `scripts\revisar_antes_de_subir.py`; luego commit en una rama nueva desde GitHub Desktop. Pasos completos en el resumen de la sesión del 03/11.
3. Revisión final a mano en Chrome con cámara real (guía en `README.md`, sección "Demostración"). El build actual (03/11 15:17) incluye F07 y F08.
4. Borrar los archivos que ya no se usan (requiere permiso de borrado; también se pueden borrar a mano):
   - `frontend/src/app/pages/inicio/` (pantallas de la etapa 1, reemplazadas por `promotor/` y `panel/`)
   - `backend/.venv/_paquetes_para_pruebas.tgz` (copia temporal para pruebas)
   - carpetas vacías `backend/.env_respaldo/` y `backend/.env.example_respaldo/` (ya ignoradas por `.gitignore`)

## Decisiones pendientes de aprobación (no bloquean)

- Login por **correo** en lugar de ID de empleado (los prototipos piden ID).
- **Duración del bloqueo** tras 3 intentos fallidos: hoy solo se cuentan los intentos.
- **Tolerancia 20 frente a 30 min**: hoy son parámetros separados (retardo 20, alerta 30).
- **Cierre de jornada con tiendas pendientes**: permitido con motivo y genera incidencia.
- **Cantidad de tiendas por día**: advertencia fuera de 3-4, sin bloqueo.
- **Excel**, **Gerente de Zona** y **"solicitudes de ajuste"** (RF-15): sin especificación suficiente.
- **WhatsApp o push**: hoy solo notificación interna.

## Datos de prueba en la base real

- Usuarios de prueba: `admin.prueba@`, `supervisor.prueba@`, `promotor.prueba@` e `inactivo.prueba@scribetracker.test`. Sus contraseñas están solo en `scripts\logs\usuarios_prueba.txt` (no se sube a Git).
- `scripts\datos_demo.bat` crea 4 tiendas de León y asigna las tiendas del día al promotor de prueba. Las coordenadas quedan en `scripts\logs\datos_demo.log`.
- En la base real quedaron registros de la demostración del 02/11: una jornada, 2 visitas, 7 fotos y un reporte.

## Archivos clave

- Backend: `backend/app/models/operacion.py` (modelo), `backend/app/servicios/operacion.py` (reglas), `backend/app/routes/*.py` (API).
- Migración: `backend/migrations/versions/c87399dedb00_etapa_2_tiendas_rutas_jornadas.py`.
- Frontend: `frontend/src/app/promotor/` (móvil), `frontend/src/app/panel/` (supervisión y administración), `frontend/src/app/core/cola.service.ts` (sin conexión).
- Pruebas: `backend/tests/`, `scripts/pruebas.bat`, `docs/pruebas/`.
- Evidencias: `scripts/evidencias/` (casos, ejecución en SQL Server, capturas de interfaz con Playwright, reproducción de F08, generador y verificador del reporte), `docs/evidencias/`, `docs/REPORTE_PRUEBAS.md`.
- Documentos: `docs/MATRIZ_REQUISITOS.md`, este archivo y `README.md`.
