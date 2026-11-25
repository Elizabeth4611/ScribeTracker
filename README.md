# ScribeTracker

Sistema web para monitorear las jornadas de los promotores de **Scribe (Bio Pappel)** en las tiendas.

- **Sistema publicado:** https://scribetracker.azurewebsites.net
- **Proyecto de:** Ingeniería de Software · Instituto Tecnológico de León · Docente: Ruth Saez de Nanclares
- **Equipo:** Ramos Infante Esmeralda Elizabeth · Faire Mariche Siomara Mabel · García Castillo Jorge Paolo

## Qué hace

| Rol | Qué puede hacer |
|---|---|
| **Promotor** (celular) | Iniciar la jornada con foto de entrada dentro de la geocerca de su primera tienda; hacer check-in y check-out en cada tienda con 6 fotografías (Entrada, Anaquel antes, Anaquel después, Precios, Promociones y Salida); tomar pausas de comida y descanso; enviar su ubicación durante la jornada; trabajar sin conexión (los registros se guardan y se envían al volver la señal); pedir ajustes a su supervisor; ver su historial. |
| **Supervisor** (computadora) | Ver en un mapa en tiempo real dónde está cada promotor y sus alertas; revisar rutas del día, incidencias y fotografías; aprobar o rechazar solicitudes de ajuste; generar reportes en PDF; recibir notificaciones push de alertas críticas. |
| **Administrador** | Todo lo del supervisor, más la gestión de usuarios (alta, edición, desactivar, eliminar sin historial, contraseña temporal), tiendas con su geocerca, rutas y los parámetros del sistema. |

Todos los roles tienen en **Configuración → Ayuda** el manual de usuario en PDF.

## Tecnologías

- **Backend:** Python 3.13 (3.12 en Azure), Flask 3, SQLAlchemy 2, Flask-Migrate (Alembic) para las migraciones, ReportLab para los PDF y pywebpush para las notificaciones.
- **Frontend:** Angular 21 y Leaflet para los mapas.
- **Base de datos:** SQL Server (SQL Server Express en local, Azure SQL Database en internet).
- **Publicación:** Azure App Service (Linux) con gunicorn.

## Estructura

```
backend/
  app/
    models/      Tablas de la base de datos (Usuario, Tienda, Ruta, Jornada, Visita, Evidencia, ...)
    routes/      API REST: una ruta por módulo (auth, usuarios, tiendas, rutas, promotor, supervision, ...)
    servicios/   Reglas del negocio: geocerca, alertas, reportes PDF, push, parámetros, ...
    auth.py      Sesión, roles y permisos
  migrations/    Versiones de la base de datos (Alembic)
  tests/         181 pruebas automáticas (pytest)
  config.py      Configuración (lee backend/.env)
  wsgi.py        Punto de entrada para el servidor de producción
frontend/
  src/app/
    core/        Servicios compartidos: sesión, API, cola sin conexión, GPS, push
    pages/       Inicio de sesión y cambio de contraseña
    promotor/    Pantallas del promotor (vista de celular)
    panel/       Pantallas del supervisor y del administrador
    shared/      Componentes reutilizables: cámara, mapa, avisos
  src/ayuda/     Manual de usuario (PDF)
despliegue/azure/  Scripts para publicar en Azure
scripts/           Scripts de Windows para instalar, iniciar y probar
```

## Instalación en Windows (primera vez)

Requisitos: Python 3.13, Node.js 20.19+, 22.12+ o 24+, SQL Server Express con **ODBC Driver 18 for SQL Server**.

1. En SQL Server crea una base vacía: `CREATE DATABASE ScribeTracker;`
2. Copia `backend\.env.example` como `backend\.env` y llena sus datos (servidor de SQL y una `SECRET_KEY` propia).
3. Ejecuta `scripts\instalar.bat`: crea el entorno de Python, instala las dependencias, crea las tablas y prepara Angular.
4. Ejecuta `scripts\crear_admin.bat` para crear el primer administrador.

## Uso diario

Ejecuta `scripts\abrir_scribetracker.bat`. Enciende SQL Server si hace falta, arranca Flask (`http://127.0.0.1:5000`) y Angular, y abre **http://localhost:4200**.

La cámara y el GPS del navegador solo funcionan en `localhost` o con HTTPS. Para simular la ubicación en la laptop: Chrome → `F12` → menú ⋮ → *More tools* → **Sensors** → *Location*.

## Pruebas automáticas

`scripts\pruebas.bat`, o a mano dentro de `backend`:

```
.venv\Scripts\activate
python -m pytest
```

Usan una base SQLite en memoria, así que no tocan la base real.

## Publicación en Azure

- `despliegue/azure/construir_paquete.sh` compila Angular y arma el paquete para Linux.
- `despliegue/azure/startup.sh` es el comando de inicio del App Service (`bash startup.sh`): instala el controlador ODBC si falta, prepara la carpeta de fotos y arranca gunicorn.
- La conexión a Azure SQL se configura en el App Service con `DB_SERVER`, `DB_NAME`, `DB_USER` y `DB_PASSWORD`. La contraseña nunca está en el código.
- `scripts\azure_bd.bat` aplica las migraciones en la base de Azure.
