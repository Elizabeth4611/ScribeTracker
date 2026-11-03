# Registro de pruebas · ScribeTracker

Documento generado con `python scripts/generar_registro_pruebas.py` a partir del código de las pruebas y de los resultados reales (JUnit). No contiene resultados inventados.

## Resumen

- Pruebas automáticas del backend: **81** funciones de prueba (algunas parametrizadas: la matriz de permisos ejecuta 9 casos).
- Laptop Windows · SQL Server (base ScribeTracker_Pruebas): **81 de 81** exitosas en la última ejecución.
- Laptop Windows · SQLite en memoria: **81 de 81** exitosas en la última ejecución.
- Pruebas de interfaz de punta a punta en la laptop: **9** (ver sección E2E).
- Fallos reales encontrados y corregidos: **7** (ver Historial de fallos).

Tipos: *válido* (datos correctos), *inválido* (datos incorrectos o estado incompatible), *no autorizado* (permisos o petición manipulada).

Entornos:

- **Laptop Windows · SQL Server**: Python 3.13, Flask, SQLAlchemy y SQL Server Express de la laptop; base de datos separada `ScribeTracker_Pruebas` (nunca la base real).
- **Laptop Windows · SQLite**: las mismas pruebas con SQLite en memoria.
- **Entorno de desarrollo (Linux, SQLite)**: donde se ejecutaron por primera vez y se detectaron F01-F06.

## Historial de fallos y correcciones

| ID | Prueba | Tipo de fallo | Causa | Archivo y cambio | Re-ejecución | Evidencia |
|---|---|---|---|---|---|---|
| F01 | AUT01 test_login_correcto_devuelve_rol_sin_hash | Fallo de la prueba (aserción demasiado amplia); el sistema no exponía contraseñas | La prueba buscaba la palabra "password" en toda la respuesta y la nueva bandera booleana debe_cambiar_password la contenía. | `backend/tests/test_auth.py`: Se verifica que ni la contraseña ni su hash (completo o parcial) aparezcan en la respuesta, y que no existan las claves password/password_hash. | Misma prueba: 1 passed (entorno de desarrollo); 91/91 en la laptop | `evidencias/F01_antes_password_en_respuesta.txt` / `evidencias/F01_despues_password_en_respuesta.txt` |
| F02 | U10 La contraseña temporal obliga a cambiarla | Defecto real del sistema (error 500 en tiempo de ejecución) | error(mensaje, codigo, **extra) recibía también codigo="cambiar_password" como dato extra: TypeError al responder a un usuario con contraseña temporal. | `backend/app/auth.py`: El parámetro del código HTTP se renombró a http; el dato extra codigo queda en la respuesta JSON. | Misma prueba: 1 passed; suite completa 44 passed | `evidencias/F02_antes_error_codigo_duplicado.txt` / `evidencias/F02_despues_error_codigo_duplicado.txt` |
| F03 | J07 Flujo completo de la jornada | Error en los datos de la prueba; el sistema aplicó correctamente la regla | El check-in se programó a las 08:00, antes del inicio de jornada (08:05). El servidor respondió 400 "La hora del registro es anterior al inicio de tu jornada". | `backend/tests/test_jornada.py`: La primera visita empieza a las 08:10 (y su salida a las 09:40). | Misma prueba: 1 passed | `evidencias/F03_antes_J07_checkin_antes_de_jornada.txt` / `evidencias/F03_despues_J07_checkin_antes_de_jornada.txt` |
| F04 | S01 Mapa y alcance del supervisor | Error en el diseño de la prueba | Se esperaban 3 promotores para el administrador, pero los datos base de la etapa 1 incluyen a "Pedro Promotor" (activo, sin número de empleado). | `backend/tests/test_supervision_reportes.py`: Se comparan los nombres de los 4 promotores activos. | Misma prueba: 1 passed | `evidencias/F04_antes_S01_mapa_y_alcance_supervisor.txt` / `evidencias/F04_despues_S01_mapa_y_alcance_supervisor.txt` |
| F05 | S02 Ubicación desactualizada | Error en el diseño de la prueba | La prueba tomaba el primer promotor de la lista suponiendo que era P1; la lista se ordena por nombre (Julieta antes que Marco). | `backend/tests/test_supervision_reportes.py`: Se busca a P1 por su número de empleado. | Misma prueba: 1 passed | `evidencias/F05_antes_S02_ubicacion_desactualizada.txt` / `evidencias/F05_despues_S02_ubicacion_desactualizada.txt` |
| F06 | REP02 Exportar reporte de exhibición a PDF | Defecto real del sistema (error 500 al exportar) | reportlab lee las imágenes al construir el documento; un archivo de evidencia dañado o no decodificable hacía fallar todo el PDF (OSError). | `backend/app/servicios/reportes.py`: Nueva función _imagen_segura: verifica cada imagen con Pillow antes de incluirla y la sustituye por "(imagen no disponible)" si es inválida. | Misma prueba: 1 passed; además REP04 confirma 4 fotos reales incrustadas | `evidencias/F06_antes_REP02_pdf_y_permisos.txt` / `evidencias/F06_despues_REP02_pdf_y_permisos.txt` |
| F07 | E2E-07 Sincronización sin conexión en la interfaz | Defecto real del sistema (la cola sin conexión nunca reintentaba) | En ColaService.sincronizar(), sin pendientes la función async terminaba de forma síncrona y su finally limpiaba enCurso antes de asignarse la promesa; enCurso quedaba ocupado y no se volvía a sincronizar. | `frontend/src/app/core/cola.service.ts`: La promesa se guarda en una variable y enCurso se libera en .finally() solo si sigue siendo la misma ejecución. | Misma prueba en la laptop: los 2 eventos pendientes se enviaron al recargar; 0 pendientes; registros con origen "Sin conexión" y horas de captura conservadas | `evidencias/F07_antes_sincronizacion_bloqueada.txt` / `evidencias/F07_despues_sincronizacion_bloqueada.txt` |

## Pruebas de interfaz (E2E) en la laptop

Ejecutadas en el navegador integrado contra Flask + SQL Server real (base `ScribeTracker`) con los usuarios de prueba. La ubicación GPS y la cámara se simularon dentro de la página (equivalente a *Sensores* de Chrome DevTools), porque la laptop no está físicamente en las tiendas.

| ID | Requisito | Procedimiento | Esperado | Obtenido | Estado |
|---|---|---|---|---|---|
| E2E-01 | RF-01; regla C2 | Ubicación simulada en Soriana (tienda 2) y botón INICIAR JORNADA | Rechazo con distancia y radio | Aviso: "Para iniciar tu jornada debes estar en tu primera tienda: Walmart Torres Landa. Estás a 2297 m y el radio permitido es de 90 m." | exitosa |
| E2E-02 | RF-01; reglas C1-C2 | Ubicación a ~22 m de Walmart Torres Landa e INICIAR JORNADA | Jornada iniciada y rastreo activo | Aviso "Jornada iniciada. El seguimiento de ubicación está activo."; estado "Jornada activa"; aparecen los botones CHECK-IN | exitosa |
| E2E-03 | RF-03, RF-04; regla D | CHECK-IN en Walmart; TOMAR FOTOS; CHECK-OUT sin fotos | Check-in registrado; check-out rechazado con categorías faltantes | "Check-in registrado correctamente en Walmart Torres Landa." y "Faltan fotografías válidas para cerrar la visita: Anaquel antes, Anaquel después, Precios, Promociones." | exitosa |
| E2E-04 | RF-05, RF-06, RF-12 | Foto Precios a 400 m; fotos de las 4 categorías a 11 m (Promociones marcada como exhibición sin promoción) | La foto lejana se guarda sin contar; las 4 categorías quedan válidas | "La foto se guardó pero NO cuenta para la visita: Tomada a 399 m de la tienda (radio 90 m)."; lista ✔ en las 4 categorías; galería: Precios Fuera de geocerca (400 m) y 4 Válidas (11 m) | exitosa |
| E2E-05 | RF-04; reglas C5-C7 | CHECK-OUT a ~30 m | Visita cerrada, jornada abierta | "Check-out registrado. Tiempo en tienda: 0 h 1 min. Tu jornada sigue abierta."; Walmart "Visitada", Soriana "Por visitar" con CHECK-IN; estado "Jornada activa" | exitosa |
| E2E-06 | RF-02, RF-08 | Pausas > DESCANSO; POST /api/promotor/ubicaciones durante la pausa; FINALIZAR | Pausa iniciada, rastreo suspendido y punto rechazado | "Pausa de descanso iniciada (20 min). El seguimiento de ubicación está detenido."; servidor: estado_jornada "En pausa", estado_conexion "Rastreo suspendido", rastreo_activo false; ubicación 409 "El seguimiento está suspendido durante la pausa."; "Pausa finalizada. Rastreo reactivado." | exitosa |
| E2E-07 | RNF-08, RNF-09 | Check-in en Soriana y foto sin red; restaurar red | Eventos marcados como pendientes (no validados) y enviados al volver la red | Primera ejecución: pendientes correctos pero NO se sincronizaron (defecto F07). Tras la corrección: 0 pendientes; visita Soriana con origen "Sin conexión"; foto capturada 23:23:17, recibida 23:25:03 | fallida → corregida → exitosa |
| E2E-08 | RF-10, RF-11 | Abrir Módulo de supervisión | Estados separados, última ubicación y alertas críticas | Resumen: En tienda 1; tabla: Activo · En jornada · En tienda Soriana San Juan Bosco · Reciente · 23:21 · visitas 1/4 · pausas 1; alerta crítica "Foto fuera de geocerca" | exitosa |
| E2E-09 | RF-13, RF-15, RF-16 | Generar reporte Diario de Exhibición del 02/11/2026 y descargar PDF | Métricas iguales a los registros y PDF con fotos | 201 "Reporte generado."; asignadas 4, visitadas 1, fotos 5 válidas de 6, 1 fuera de geocerca, 2 incidencias; PDF 67,655 bytes (%PDF-1.4) con 5 imágenes | exitosa |

## Detalle de pruebas automáticas

### AUT01 · Login correcto devuelve rol sin hash

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_login_correcto_devuelve_rol_sin_hash -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Historial:** falló antes de la corrección F01 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_login_correcto_devuelve_rol_sin_hash(client):
    r = login(client, "promotor@test.mx")
    assert r.status_code == 200
    usuario = r.get_json()["usuario"]
    assert usuario["rol"] == "Promotor"
    assert "password_hash" not in usuario
    assert "password" not in usuario
    # Corrección F01: la comprobación anterior buscaba la palabra
    # "password" en todo el texto y fallaba con la bandera booleana
    # debe_cambiar_password. Ahora se verifica lo importante: que ni la
    # contraseña ni su hash aparezcan en la respuesta.
    texto = r.get_data(as_text=True)
    assert PASSWORD not in texto
    with client.application.app_context():
        h = db.session.execute(db.select(Usuario.password_hash).where(
            Usuario.correo_electronico == "promotor@test.mx")).scalar_one()
    assert h not in texto and h.split("$")[-1] not in texto
```

</details>

### AUT02 · Correo sin distinguir mayusculas ni espacios

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_correo_sin_distinguir_mayusculas_ni_espacios -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_correo_sin_distinguir_mayusculas_ni_espacios(client):
    assert login(client, "  PROMOTOR@Test.mx ").status_code == 200
```

</details>

### AUT03 · Contrasena incorrecta

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_contrasena_incorrecta -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_contrasena_incorrecta(client):
    r = login(client, "promotor@test.mx", "otra-cosa")
    assert r.status_code == 401
    assert r.get_json()["error"] == "Correo o contraseña incorrectos."
```

</details>

### AUT04 · Correo inexistente mismo mensaje

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_correo_inexistente_mismo_mensaje -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_correo_inexistente_mismo_mensaje(client):
    r = login(client, "nadie@test.mx")
    assert r.status_code == 401
    assert r.get_json()["error"] == "Correo o contraseña incorrectos."
```

</details>

### AUT05 · Campos vacios

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_campos_vacios -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_campos_vacios(client):
    assert login(client, "", "").status_code == 400
```

</details>

### AUT06 · Login exige json

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_login_exige_json -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_login_exige_json(client):
    r = client.post("/api/auth/login", data={"correo": "a", "password": "b"})
    assert r.status_code == 415
```

</details>

### AUT07 · Usuario inactivo no entra

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_usuario_inactivo_no_entra -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_usuario_inactivo_no_entra(client):
    r = login(client, "inactivo@test.mx")
    assert r.status_code == 403
    assert "inactiva" in r.get_json()["error"]
    assert client.get("/api/auth/me").status_code == 401
```

</details>

### AUT08 · Inactivo con contrasena mala no revela estatus

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_inactivo_con_contrasena_mala_no_revela_estatus -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_inactivo_con_contrasena_mala_no_revela_estatus(client):
    r = login(client, "inactivo@test.mx", "mala-clave")
    assert r.status_code == 401
```

</details>

### AUT09 · Me sin sesion

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_me_sin_sesion -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_me_sin_sesion(client):
    assert client.get("/api/auth/me").status_code == 401
```

</details>

### AUT10 · Me con sesion

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_me_con_sesion -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_me_con_sesion(client):
    login(client, "admin@test.mx")
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.get_json()["usuario"]["rol"] == "Administrador"
```

</details>

### AUT11 · Cookie httponly

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_cookie_httponly -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_cookie_httponly(client):
    r = login(client, "admin@test.mx")
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
```

</details>

### AUT12 · Logout cierra sesion

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_logout_cierra_sesion -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_logout_cierra_sesion(client):
    login(client, "admin@test.mx")
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/inicio/administrador").status_code == 401
```

</details>

### AUT13 · Desactivar usuario invalida sesion abierta

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_desactivar_usuario_invalida_sesion_abierta -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_desactivar_usuario_invalida_sesion_abierta(client, app):
    login(client, "promotor@test.mx")
    assert client.get("/api/inicio/promotor").status_code == 200
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.estatus = "Inactivo"
        db.session.commit()
    assert client.get("/api/inicio/promotor").status_code == 401
```

</details>

### AUT14 · Cambiar contrasena invalida sesion abierta

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_cambiar_contrasena_invalida_sesion_abierta -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_cambiar_contrasena_invalida_sesion_abierta(client, app):
    login(client, "promotor@test.mx")
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.set_password("Nueva-clave-5678")
        db.session.commit()
    assert client.get("/api/auth/me").status_code == 401
```

</details>

### AUT15 · Cambiar rol cambia permisos

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_cambiar_rol_cambia_permisos -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_cambiar_rol_cambia_permisos(client, app):
    login(client, "promotor@test.mx")
    with app.app_context():
        u = db.session.execute(
            db.select(Usuario).where(Usuario.correo_electronico == "promotor@test.mx")
        ).scalar_one()
        u.rol = "Supervisor"
        db.session.commit()
    assert client.get("/api/inicio/promotor").status_code == 403
    assert client.get("/api/inicio/supervisor").status_code == 200
```

</details>

### AUT16 · Matriz de permisos

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_matriz_de_permisos -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas (9 casos) → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas (9 casos) → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_matriz_de_permisos(client, rol_usuario, rol_ruta):
    login(client, ACCESOS[rol_usuario])
    esperado = 200 if rol_usuario == rol_ruta else 403
    assert client.get(RUTAS[rol_ruta]).status_code == esperado
```

</details>

### AUT17 · Inicio sin sesion

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_inicio_sin_sesion -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas (3 casos) → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas (3 casos) → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_inicio_sin_sesion(client, ruta):
    assert client.get(ruta).status_code == 401
```

</details>

### AUT18 · Supervisor ve a sus promotores

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_supervisor_ve_a_sus_promotores -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_supervisor_ve_a_sus_promotores(client):
    login(client, "supervisor@test.mx")
    datos = client.get("/api/inicio/supervisor").get_json()
    assert [p["correo_electronico"] for p in datos["promotores"]] == ["promotor@test.mx"]
```

</details>

### AUT19 · Promotor ve a su supervisor

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_promotor_ve_a_su_supervisor -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_promotor_ve_a_su_supervisor(client):
    login(client, "promotor@test.mx")
    datos = client.get("/api/inicio/promotor").get_json()
    assert datos["supervisor"]["correo_electronico"] == "supervisor@test.mx"
```

</details>

### AUT20 · Admin ve resumen

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_admin_ve_resumen -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_admin_ve_resumen(client):
    login(client, "admin@test.mx")
    datos = client.get("/api/inicio/administrador").get_json()
    assert datos["total_usuarios"] == 4
    assert datos["resumen_usuarios"]["Promotor"] == {"Activo": 1, "Inactivo": 1}
```

</details>

### AUT21 · Sin secret key no arranca

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_sin_secret_key_no_arranca -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_sin_secret_key_no_arranca():
    class SinClave(ConfigPruebas):
        SECRET_KEY = None

    from app import create_app

    with pytest.raises(RuntimeError):
        create_app(SinClave)
```

</details>

### AUT22 · Cookie alterada no sirve

- **Requisito / caso de uso:** RF-01/RF-02 (3.6) Inicio y cierre de sesión; RNF-16
- **Tipo:** etapa 1
- **Precondiciones:** —
- **Datos de entrada:** —
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_auth.py::test_cookie_alterada_no_sirve -v`
- **Resultado esperado:** Las aserciones del código se cumplen
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** Aserciones cumplidas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** Aserciones cumplidas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_cookie_alterada_no_sirve(client):
    login(client, "promotor@test.mx")
    client.set_cookie("scribetracker_session", "valor.falsificado.xyz")
    assert client.get("/api/auth/me").status_code == 401
```

</details>

### J01 · Iniciar jornada dentro de la geocerca de la primera tienda

- **Requisito / caso de uso:** RF-01 Inicio de jornada; reglas C1 y C2
- **Tipo:** válido
- **Precondiciones:** P1 con Walmart (orden 1) y Soriana (orden 2) asignadas hoy; 08:05
- **Datos de entrada:** ubicación a 10 m de Walmart Torres Landa
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J01_inicio_en_primera_tienda -v`
- **Resultado esperado:** HTTP 201; jornada Abierta; rastreo activo; primer punto de ubicación registrado
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Jornada iniciada. El seguimiento de ubicación está activo. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Jornada iniciada. El seguimiento de ubicación está activo. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J01_inicio_en_primera_tienda(app, esc, obs):
    """J01 · Iniciar jornada dentro de la geocerca de la primera tienda
    RF: RF-01 Inicio de jornada; reglas C1 y C2
    Tipo: válido
    Pre: P1 con Walmart (orden 1) y Soriana (orden 2) asignadas hoy; 08:05
    Entrada: ubicación a 10 m de Walmart Torres Landa
    Esperado: HTTP 201; jornada Abierta; rastreo activo; primer punto de ubicación registrado
    """
    c = _p1(app)
    r = obs(_iniciar(c, esc))
    assert r.status_code == 201 and r.get_json()["jornada"]["estado"] == "Abierta"
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["rastreo_activo"] is True and hoy["estado"]["estado_jornada"] == "En jornada"
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Ubicacion)).scalar_one() == 1
```

</details>

### J02 · Iniciar jornada fuera de la geocerca o en otra tienda asignada

- **Requisito / caso de uso:** RF-01; regla C2
- **Tipo:** inválido
- **Precondiciones:** P1 sin jornada
- **Datos de entrada:** (a) a 120 m de Walmart; (b) dentro de Soriana, que es la tienda 2
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J02_inicio_fuera_de_primera_tienda -v`
- **Resultado esperado:** HTTP 409 en ambos casos con la distancia; no se crea jornada
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Para iniciar tu jornada debes estar en tu primera tienda: Walmart Torres Landa. Estás a 119 m y el radio permitido es de 50 m. · {'distancia_m': 119.9} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Para iniciar tu jornada debes estar en tu primera tienda: Walmart Torres Landa. Estás a 119 m y el radio permitido es de 50 m. · {'distancia_m': 119.9} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J02_inicio_fuera_de_primera_tienda(app, esc, obs):
    """J02 · Iniciar jornada fuera de la geocerca o en otra tienda asignada
    RF: RF-01; regla C2
    Tipo: inválido
    Pre: P1 sin jornada
    Entrada: (a) a 120 m de Walmart; (b) dentro de Soriana, que es la tienda 2
    Esperado: HTTP 409 en ambos casos con la distancia; no se crea jornada
    """
    c = _p1(app)
    r = obs(_iniciar(c, esc, metros=120))
    assert r.status_code == 409 and r.get_json()["distancia_m"] > 50
    assert c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[1], 5)).status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Jornada)).scalar_one() == 0
```

</details>

### J03 · Una sola jornada por fecha operativa

- **Requisito / caso de uso:** RF-01; regla C1
- **Tipo:** inválido (duplicado)
- **Precondiciones:** P1 ya inició y finalizó su jornada hoy (cierre forzado con motivo)
- **Datos de entrada:** segundo intento de iniciar jornada el mismo día
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J03_jornada_unica_por_fecha -v`
- **Resultado esperado:** HTTP 409 "Ya registraste una jornada para este día"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Ya registraste una jornada para este día. Solo se permite una jornada por fecha. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Ya registraste una jornada para este día. Solo se permite una jornada por fecha. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J03_jornada_unica_por_fecha(app, esc, obs):
    """J03 · Una sola jornada por fecha operativa
    RF: RF-01; regla C1
    Tipo: inválido (duplicado)
    Pre: P1 ya inició y finalizó su jornada hoy (cierre forzado con motivo)
    Entrada: segundo intento de iniciar jornada el mismo día
    Esperado: HTTP 409 "Ya registraste una jornada para este día"
    """
    c = _p1(app)
    _iniciar(c, esc)
    c.post("/api/promotor/jornada/finalizar", json={**punto(esc.coords[0]), "forzar": True,
                                                   "motivo": "Prueba de jornada única"})
    r = obs(_iniciar(c, esc))
    assert r.status_code == 409 and "una jornada" in r.get_json()["error"]
```

</details>

### J04 · Promotor sin tiendas asignadas no puede iniciar

- **Requisito / caso de uso:** RF-01 (dependencia de RF-09)
- **Tipo:** inválido
- **Precondiciones:** P2 no tiene asignaciones hoy
- **Datos de entrada:** iniciar jornada en cualquier punto
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J04_sin_tiendas_asignadas -v`
- **Resultado esperado:** HTTP 409 "No tienes tiendas asignadas para hoy"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No tienes tiendas asignadas para hoy. Consulta a tu supervisor. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No tienes tiendas asignadas para hoy. Consulta a tu supervisor. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J04_sin_tiendas_asignadas(app, esc, obs):
    """J04 · Promotor sin tiendas asignadas no puede iniciar
    RF: RF-01 (dependencia de RF-09)
    Tipo: inválido
    Pre: P2 no tiene asignaciones hoy
    Entrada: iniciar jornada en cualquier punto
    Esperado: HTTP 409 "No tienes tiendas asignadas para hoy"
    """
    r = obs(cliente(app, "p2@test.mx").post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0])))
    assert r.status_code == 409 and "asignadas" in r.get_json()["error"]
```

</details>

### J05 · Inicio después de la tolerancia genera incidencia de retardo

- **Requisito / caso de uso:** RF-11/RF-15 (cumplimiento de horarios); parámetro tolerancia_retardo_min = 20 (entrevista P16)
- **Tipo:** válido (genera incidencia no crítica)
- **Precondiciones:** hora 08:35
- **Datos de entrada:** iniciar jornada dentro de la primera tienda
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J05_retardo_registrado -v`
- **Resultado esperado:** HTTP 201 e incidencia "Retardo" no crítica
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Jornada iniciada. El seguimiento de ubicación está activo. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Jornada iniciada. El seguimiento de ubicación está activo. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J05_retardo_registrado(app, esc, obs):
    """J05 · Inicio después de la tolerancia genera incidencia de retardo
    RF: RF-11/RF-15 (cumplimiento de horarios); parámetro tolerancia_retardo_min = 20 (entrevista P16)
    Tipo: válido (genera incidencia no crítica)
    Pre: hora 08:35
    Entrada: iniciar jornada dentro de la primera tienda
    Esperado: HTTP 201 e incidencia "Retardo" no crítica
    """
    a_las(8, 35)
    r = obs(_iniciar(_p1(app), esc))
    assert r.status_code == 201
    with app.app_context():
        inc = db.session.execute(db.select(Incidencia)).scalar_one()
        assert inc.tipo == "Retardo" and not inc.es_critica
```

</details>

### V01 · Check-in separado del inicio de jornada

- **Requisito / caso de uso:** RF-03 Check-in; reglas C3 y C4
- **Tipo:** válido
- **Precondiciones:** P1 con jornada iniciada a las 08:05 y sin visitas
- **Datos de entrada:** 08:10 check-in en Walmart a 15 m
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V01_checkin_independiente_del_inicio -v`
- **Resultado esperado:** iniciar jornada no crea visita; el check-in crea visita Abierta con su propia hora y ubicación
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Check-in registrado correctamente en Walmart Torres Landa. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Check-in registrado correctamente en Walmart Torres Landa. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V01_checkin_independiente_del_inicio(app, esc, obs):
    """V01 · Check-in separado del inicio de jornada
    RF: RF-03 Check-in; reglas C3 y C4
    Tipo: válido
    Pre: P1 con jornada iniciada a las 08:05 y sin visitas
    Entrada: 08:10 check-in en Walmart a 15 m
    Esperado: iniciar jornada no crea visita; el check-in crea visita Abierta con su propia hora y ubicación
    """
    c = _p1(app)
    _iniciar(c, esc)
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 0
    a_las(8, 10)
    r = obs(_checkin(c, esc, metros=15))
    v = r.get_json()["visita"]
    assert r.status_code == 201 and v["estado"] == "Abierta"
    assert v["checkin"].endswith("08:10:00") and 14 < v["distancia_checkin_m"] < 16
```

</details>

### V02 · Check-in sin jornada y fuera de la geocerca

- **Requisito / caso de uso:** RF-03 (dependencia RF-01); regla C4
- **Tipo:** inválido
- **Precondiciones:** P1 sin jornada; después con jornada
- **Datos de entrada:** (a) check-in sin jornada; (b) check-in a 80 m de Walmart
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V02_checkin_requiere_jornada_y_geocerca -v`
- **Resultado esperado:** (a) 409 "Primero inicia tu jornada"; (b) 409 "No estás dentro del radio permitido"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 79 m y el radio es de 50 m. · {'distancia_m': 79.9} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 79 m y el radio es de 50 m. · {'distancia_m': 79.9} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V02_checkin_requiere_jornada_y_geocerca(app, esc, obs):
    """V02 · Check-in sin jornada y fuera de la geocerca
    RF: RF-03 (dependencia RF-01); regla C4
    Tipo: inválido
    Pre: P1 sin jornada; después con jornada
    Entrada: (a) check-in sin jornada; (b) check-in a 80 m de Walmart
    Esperado: (a) 409 "Primero inicia tu jornada"; (b) 409 "No estás dentro del radio permitido"
    """
    c = _p1(app)
    r = _checkin(c, esc)
    assert r.status_code == 409 and "inicia tu jornada" in r.get_json()["error"]
    _iniciar(c, esc)
    r = obs(_checkin(c, esc, metros=80))
    assert r.status_code == 409 and "radio permitido" in r.get_json()["error"]
```

</details>

### V03 · Impedir dos visitas abiertas simultáneas y visita duplicada

- **Requisito / caso de uso:** RF-03; regla C9
- **Tipo:** inválido (estado incompatible)
- **Precondiciones:** P1 con visita abierta en Walmart
- **Datos de entrada:** check-in en Soriana (dentro de su geocerca) y repetir check-in en Walmart
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V03_dos_visitas_abiertas -v`
- **Resultado esperado:** HTTP 409 en ambos; solo existe una visita
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Ya tienes una visita abierta en Walmart. Registra su check-out antes de entrar a otra tienda. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Ya tienes una visita abierta en Walmart. Registra su check-out antes de entrar a otra tienda. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V03_dos_visitas_abiertas(app, esc, obs):
    """V03 · Impedir dos visitas abiertas simultáneas y visita duplicada
    RF: RF-03; regla C9
    Tipo: inválido (estado incompatible)
    Pre: P1 con visita abierta en Walmart
    Entrada: check-in en Soriana (dentro de su geocerca) y repetir check-in en Walmart
    Esperado: HTTP 409 en ambos; solo existe una visita
    """
    c = _p1(app)
    _iniciar(c, esc)
    _checkin(c, esc)
    r = obs(_checkin(c, esc, idx=1, metros=5))
    assert r.status_code == 409 and "visita abierta" in r.get_json()["error"]
    assert _checkin(c, esc).status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 1
```

</details>

### E01 · Fotografía válida vinculada a visita y categoría con ubicación propia

- **Requisito / caso de uso:** RF-05, RF-06, RNF-13; reglas D (fecha, hora, ubicación propia, validación guardada)
- **Tipo:** válido
- **Precondiciones:** visita abierta en Walmart
- **Datos de entrada:** foto JPEG "Anaquel antes" a 20 m de la tienda
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_E01_foto_valida_con_ubicacion_propia -v`
- **Resultado esperado:** HTTP 201; estatus Válida; se guardan hash SHA-256, distancia, coordenadas y hora propias
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Foto guardada correctamente (Anaquel antes). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Foto guardada correctamente (Anaquel antes). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_E01_foto_valida_con_ubicacion_propia(app, esc, obs):
    """E01 · Fotografía válida vinculada a visita y categoría con ubicación propia
    RF: RF-05, RF-06, RNF-13; reglas D (fecha, hora, ubicación propia, validación guardada)
    Tipo: válido
    Pre: visita abierta en Walmart
    Entrada: foto JPEG "Anaquel antes" a 20 m de la tienda
    Esperado: HTTP 201; estatus Válida; se guardan hash SHA-256, distancia, coordenadas y hora propias
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    a_las(8, 20)
    r = obs(subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 20)))
    e = r.get_json()["evidencia"]
    assert r.status_code == 201 and e["estatus_validacion"] == "Válida" and e["dentro_geocerca"]
    assert len(e["hash_imagen"]) == 64 and 19 < e["distancia_m"] < 21 and e["fecha_hora_captura"].endswith("08:20:00")
    assert c.get(e["url"]).status_code == 200
```

</details>

### E02 · Fotografía fuera de la geocerca se guarda pero no cuenta

- **Requisito / caso de uso:** RF-12 Validación automática; regla D (fuera de geocerca no completa la visita)
- **Tipo:** inválido (genera alerta)
- **Precondiciones:** visita abierta en Walmart
- **Datos de entrada:** foto "Precios" tomada a 300 m
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_E02_foto_fuera_de_geocerca_no_cuenta -v`
- **Resultado esperado:** HTTP 422; estatus "Fuera de geocerca"; incidencia crítica; la categoría Precios sigue faltando
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 422 · La foto se guardó pero NO cuenta para la visita: Tomada a 299 m de la tienda (radio 50 m). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 422 · La foto se guardó pero NO cuenta para la visita: Tomada a 299 m de la tienda (radio 50 m). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_E02_foto_fuera_de_geocerca_no_cuenta(app, esc, obs):
    """E02 · Fotografía fuera de la geocerca se guarda pero no cuenta
    RF: RF-12 Validación automática; regla D (fuera de geocerca no completa la visita)
    Tipo: inválido (genera alerta)
    Pre: visita abierta en Walmart
    Entrada: foto "Precios" tomada a 300 m
    Esperado: HTTP 422; estatus "Fuera de geocerca"; incidencia crítica; la categoría Precios sigue faltando
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0], 300)))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Fuera de geocerca"
    assert "Precios" in r.get_json()["visita"]["categorias_faltantes"]
    with app.app_context():
        inc = db.session.execute(db.select(Incidencia).where(Incidencia.tipo == "Foto fuera de geocerca")).scalar_one()
        assert inc.es_critica
```

</details>

### E03 · La misma imagen enviada dos veces se rechaza

- **Requisito / caso de uso:** RF-12 (reutilización de fotografías); Hash_Imagen del diccionario
- **Tipo:** inválido (genera alerta)
- **Precondiciones:** visita abierta; una foto ya aceptada
- **Datos de entrada:** mismos bytes de imagen con otra categoría
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_E03_foto_repetida_rechazada -v`
- **Resultado esperado:** HTTP 422, estatus Rechazada "foto repetida"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 422 · La foto se guardó pero NO cuenta para la visita: La imagen ya se había enviado antes (foto repetida). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 422 · La foto se guardó pero NO cuenta para la visita: La imagen ya se había enviado antes (foto repetida). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_E03_foto_repetida_rechazada(app, esc, obs):
    """E03 · La misma imagen enviada dos veces se rechaza
    RF: RF-12 (reutilización de fotografías); Hash_Imagen del diccionario
    Tipo: inválido (genera alerta)
    Pre: visita abierta; una foto ya aceptada
    Entrada: mismos bytes de imagen con otra categoría
    Esperado: HTTP 422, estatus Rechazada "foto repetida"
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    datos = foto()
    assert subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 5), datos=datos).status_code == 201
    r = obs(subir_foto(c, idv, "Anaquel después", punto(esc.coords[0], 5), datos=datos))
    assert r.status_code == 422 and r.get_json()["evidencia"]["estatus_validacion"] == "Rechazada"
```

</details>

### E04 · Archivo que no es imagen y categoría inexistente

- **Requisito / caso de uso:** RF-05/RF-06; RF-23
- **Tipo:** inválido
- **Precondiciones:** visita abierta
- **Datos de entrada:** (a) bytes de texto; (b) categoría "Selfie"
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_E04_archivo_no_imagen_y_categoria -v`
- **Resultado esperado:** HTTP 400 en ambos y no se guarda evidencia
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · El archivo no es una imagen JPEG, PNG o WEBP. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · El archivo no es una imagen JPEG, PNG o WEBP. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_E04_archivo_no_imagen_y_categoria(app, esc, obs):
    """E04 · Archivo que no es imagen y categoría inexistente
    RF: RF-05/RF-06; RF-23
    Tipo: inválido
    Pre: visita abierta
    Entrada: (a) bytes de texto; (b) categoría "Selfie"
    Esperado: HTTP 400 en ambos y no se guarda evidencia
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0]), datos=b"esto no es una imagen"))
    assert r.status_code == 400
    assert subir_foto(c, idv, "Selfie", punto(esc.coords[0])).status_code == 400
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Evidencia)).scalar_one() == 0
```

</details>

### V04 · Check-out bloqueado si falta alguna categoría válida

- **Requisito / caso de uso:** RF-04 Check-out; regla D (servidor comprueba las 4 categorías y comunica faltantes)
- **Tipo:** inválido
- **Precondiciones:** visita abierta con Anaquel antes y Anaquel después válidas, Precios fuera de geocerca
- **Datos de entrada:** check-out dentro de la geocerca
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V04_checkout_bloqueado_por_categorias -v`
- **Resultado esperado:** HTTP 409 con faltantes = [Precios, Promociones]; visita sigue Abierta
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Faltan fotografías válidas para cerrar la visita: Precios, Promociones. · {'faltantes': ['Precios', 'Promociones']} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Faltan fotografías válidas para cerrar la visita: Precios, Promociones. · {'faltantes': ['Precios', 'Promociones']} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V04_checkout_bloqueado_por_categorias(app, esc, obs):
    """V04 · Check-out bloqueado si falta alguna categoría válida
    RF: RF-04 Check-out; regla D (servidor comprueba las 4 categorías y comunica faltantes)
    Tipo: inválido
    Pre: visita abierta con Anaquel antes y Anaquel después válidas, Precios fuera de geocerca
    Entrada: check-out dentro de la geocerca
    Esperado: HTTP 409 con faltantes = [Precios, Promociones]; visita sigue Abierta
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    subir_foto(c, idv, "Anaquel antes", punto(esc.coords[0], 5))
    subir_foto(c, idv, "Anaquel después", punto(esc.coords[0], 5))
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 400))
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)}))
    assert r.status_code == 409 and r.get_json()["faltantes"] == ["Precios", "Promociones"]
```

</details>

### V05 · Check-out válido cierra la visita y mantiene la jornada abierta

- **Requisito / caso de uso:** RF-04; reglas C5, C6 y C7
- **Tipo:** válido
- **Precondiciones:** visita abierta con las 4 categorías válidas (Promociones como exhibición sin promoción)
- **Datos de entrada:** 09:45 check-out a 30 m (nueva ubicación)
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V05_checkout_valido_no_cierra_jornada -v`
- **Resultado esperado:** HTTP 200; visita Cerrada con hora y coordenadas de salida propias; jornada sigue Abierta; estado En traslado
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Check-out registrado. Tiempo en tienda: 1 h 40 min. Tu jornada sigue abierta. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Check-out registrado. Tiempo en tienda: 1 h 40 min. Tu jornada sigue abierta. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V05_checkout_valido_no_cierra_jornada(app, esc, obs):
    """V05 · Check-out válido cierra la visita y mantiene la jornada abierta
    RF: RF-04; reglas C5, C6 y C7
    Tipo: válido
    Pre: visita abierta con las 4 categorías válidas (Promociones como exhibición sin promoción)
    Entrada: 09:45 check-out a 30 m (nueva ubicación)
    Esperado: HTTP 200; visita Cerrada con hora y coordenadas de salida propias; jornada sigue Abierta; estado En traslado
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    for cat in CATS[:3]:
        subir_foto(c, idv, cat, punto(esc.coords[0], 5))
    assert subir_foto(c, idv, "Promociones", punto(esc.coords[0], 5), sin_promocion=True).status_code == 201
    a_las(9, 45)
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 30)}))
    v = r.get_json()["visita"]
    assert r.status_code == 200 and v["estado"] == "Cerrada" and v["checkout"].endswith("09:45:00")
    assert 29 < v["distancia_checkout_m"] < 31
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["jornada"]["estado"] == "Abierta" and hoy["estado"]["estado_visita"] == "En traslado"
```

</details>

### V06 · Check-out fuera de la geocerca

- **Requisito / caso de uso:** RF-04; regla C5
- **Tipo:** inválido
- **Precondiciones:** visita con las 4 categorías válidas
- **Datos de entrada:** check-out a 200 m
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_V06_checkout_fuera_de_geocerca -v`
- **Resultado esperado:** HTTP 409 "No estás dentro del radio permitido"; visita sigue Abierta
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 199 m y el radio es de 50 m. · {'distancia_m': 199.8} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 199 m y el radio es de 50 m. · {'distancia_m': 199.8} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_V06_checkout_fuera_de_geocerca(app, esc, obs):
    """V06 · Check-out fuera de la geocerca
    RF: RF-04; regla C5
    Tipo: inválido
    Pre: visita con las 4 categorías válidas
    Entrada: check-out a 200 m
    Esperado: HTTP 409 "No estás dentro del radio permitido"; visita sigue Abierta
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    _cuatro_fotos(c, esc, idv)
    r = obs(c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 200)}))
    assert r.status_code == 409 and "radio" in r.get_json()["error"]
```

</details>

### J06 · Cierre de jornada conforme a visitas pendientes

- **Requisito / caso de uso:** RF-01/RF-04; reglas C7, C8 y C9
- **Tipo:** inválido y válido con motivo
- **Precondiciones:** P1 visitó Walmart; Soriana sigue pendiente
- **Datos de entrada:** (a) finalizar con visita abierta; (b) finalizar sin motivo; (c) forzar con motivo
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J06_finalizar_con_pendientes -v`
- **Resultado esperado:** (a) 409 check-out pendiente; (b) 409 con pendientes [Soriana]; (c) 200 Finalizada + incidencia
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Jornada finalizada. El seguimiento de ubicación se detuvo. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Jornada finalizada. El seguimiento de ubicación se detuvo. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J06_finalizar_con_pendientes(app, esc, obs):
    """J06 · Cierre de jornada conforme a visitas pendientes
    RF: RF-01/RF-04; reglas C7, C8 y C9
    Tipo: inválido y válido con motivo
    Pre: P1 visitó Walmart; Soriana sigue pendiente
    Entrada: (a) finalizar con visita abierta; (b) finalizar sin motivo; (c) forzar con motivo
    Esperado: (a) 409 check-out pendiente; (b) 409 con pendientes [Soriana]; (c) 200 Finalizada + incidencia
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    fin = {**punto(esc.coords[0])}
    assert "check-out" in c.post("/api/promotor/jornada/finalizar", json=fin).get_json()["error"]
    _cuatro_fotos(c, esc, idv)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0])})
    r = c.post("/api/promotor/jornada/finalizar", json=fin)
    assert r.status_code == 409 and r.get_json()["pendientes"] == ["Soriana San Juan Bosco"]
    r = obs(c.post("/api/promotor/jornada/finalizar", json={**fin, "forzar": True,
                                                           "motivo": "La tienda Soriana cerró por inventario"}))
    assert r.status_code == 200 and r.get_json()["jornada"]["cierre_forzado"] is True
    with app.app_context():
        assert db.session.execute(db.select(Incidencia).where(
            Incidencia.tipo == "Jornada cerrada con tiendas pendientes")).scalar_one()
```

</details>

### J07 · Flujo completo de la jornada con dos tiendas

- **Requisito / caso de uso:** RF-01, RF-03, RF-04, RF-05, RF-06, RF-07
- **Tipo:** válido (integración)
- **Precondiciones:** P1 con Walmart y Soriana asignadas
- **Datos de entrada:** iniciar, check-in, 4 fotos, check-out en cada tienda y finalizar sin forzar
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_J07_flujo_completo -v`
- **Resultado esperado:** jornada Finalizada sin cierre forzado; historial con 2 tiendas visitadas y 8 fotos
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Jornada finalizada. El seguimiento de ubicación se detuvo. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Jornada finalizada. El seguimiento de ubicación se detuvo. → **EXITOSA**
- **Historial:** falló antes de la corrección F03 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_J07_flujo_completo(app, esc, obs):
    """J07 · Flujo completo de la jornada con dos tiendas
    RF: RF-01, RF-03, RF-04, RF-05, RF-06, RF-07
    Tipo: válido (integración)
    Pre: P1 con Walmart y Soriana asignadas
    Entrada: iniciar, check-in, 4 fotos, check-out en cada tienda y finalizar sin forzar
    Esperado: jornada Finalizada sin cierre forzado; historial con 2 tiendas visitadas y 8 fotos
    """
    c = _p1(app)
    _iniciar(c, esc)
    # Corrección F03: el check-in de la primera tienda estaba a las 08:00,
    # antes del inicio de jornada (08:05), y el servidor lo rechazó con
    # razón. Ahora la primera visita empieza a las 08:10.
    for idx, h in ((0, 8), (1, 11)):
        a_las(h, 10)
        idv = _checkin(c, esc, idx=idx, metros=5).get_json()["visita"]["id_visita"]
        _cuatro_fotos(c, esc, idv, idx=idx)
        a_las(h + 1, 40)
        assert c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[idx])}).status_code == 200
    a_las(17, 0)
    r = obs(c.post("/api/promotor/jornada/finalizar", json=punto(esc.coords[1])))
    assert r.status_code == 200 and r.get_json()["jornada"]["cierre_forzado"] is False
    h = c.get("/api/promotor/historial?fecha=2026-11-04").get_json()["resumen"]
    assert h["tiendas_visitadas"] == 2 and h["fotos"] == 8 and h["minutos_en_tienda"] == 180
```

</details>

### P01 · Pausas de comida y descanso con límite de cantidad

- **Requisito / caso de uso:** RF-08 Pausas programadas (1 comida de 60 min, 2 descansos de 20 min)
- **Tipo:** válido e inválido
- **Precondiciones:** jornada abierta
- **Datos de entrada:** comida; segunda comida; 2 descansos; tercer descanso
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_P01_pausas_y_limites -v`
- **Resultado esperado:** primera comida 201; segunda 409 "Ya has tomado tu pausa de comida hoy"; tercer descanso 409
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Ya has tomado tu pausa de comida hoy. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Ya has tomado tu pausa de comida hoy. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_P01_pausas_y_limites(app, esc, obs):
    """P01 · Pausas de comida y descanso con límite de cantidad
    RF: RF-08 Pausas programadas (1 comida de 60 min, 2 descansos de 20 min)
    Tipo: válido e inválido
    Pre: jornada abierta
    Entrada: comida; segunda comida; 2 descansos; tercer descanso
    Esperado: primera comida 201; segunda 409 "Ya has tomado tu pausa de comida hoy"; tercer descanso 409
    """
    c = _p1(app)
    _iniciar(c, esc)
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"}).status_code == 201
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 409  # una a la vez
    a_las(9, 0)
    c.post("/api/promotor/pausas/finalizar", json={})
    r = obs(c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"}))
    assert r.status_code == 409 and "comida" in r.get_json()["error"]
    for h in (10, 11):
        a_las(h, 0)
        assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 201
        a_las(h, 10)
        c.post("/api/promotor/pausas/finalizar", json={})
    assert c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"}).status_code == 409
```

</details>

### P02 · Suspensión del seguimiento durante pausas y después del cierre

- **Requisito / caso de uso:** RF-02, RF-08; Limitación 7 (no rastrea fuera de jornada ni en pausa)
- **Tipo:** inválido (el servidor rechaza puntos)
- **Precondiciones:** jornada abierta
- **Datos de entrada:** ubicación normal (09:00); pausa de descanso; ubicación en pausa; fin de pausa; cierre; ubicación tras cierre
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_P02_rastreo_suspendido_en_pausa_y_tras_cierre -v`
- **Resultado esperado:** 201, luego 409 "suspendido durante la pausa", y 409 tras finalizar; estado "Rastreo suspendido"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · El seguimiento está suspendido durante la pausa. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · El seguimiento está suspendido durante la pausa. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_P02_rastreo_suspendido_en_pausa_y_tras_cierre(app, esc, obs):
    """P02 · Suspensión del seguimiento durante pausas y después del cierre
    RF: RF-02, RF-08; Limitación 7 (no rastrea fuera de jornada ni en pausa)
    Tipo: inválido (el servidor rechaza puntos)
    Pre: jornada abierta
    Entrada: ubicación normal (09:00); pausa de descanso; ubicación en pausa; fin de pausa; cierre; ubicación tras cierre
    Esperado: 201, luego 409 "suspendido durante la pausa", y 409 tras finalizar; estado "Rastreo suspendido"
    """
    c = _p1(app)
    _iniciar(c, esc)
    a_las(9, 0)
    assert c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300)).status_code == 201
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"})
    a_las(9, 10)
    r = obs(c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300)))
    assert r.status_code == 409 and r.get_json()["codigo_rastreo"] == "en_pausa"
    hoy = c.get("/api/promotor/hoy").get_json()
    assert hoy["rastreo_activo"] is False and hoy["estado"]["estado_conexion"] == "Rastreo suspendido"
    a_las(9, 15)
    c.post("/api/promotor/pausas/finalizar", json={})
    c.post("/api/promotor/jornada/finalizar", json={**punto(esc.coords[0]), "forzar": True,
                                                   "motivo": "Prueba de rastreo tras el cierre"})
    a_las(9, 30)
    r = c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 300))
    assert r.status_code == 409 and r.get_json()["codigo_rastreo"] == "sin_jornada"
```

</details>

### P03 · No se registran check-in ni fotos durante una pausa

- **Requisito / caso de uso:** RF-08; regla C9 (estados incompatibles)
- **Tipo:** inválido
- **Precondiciones:** jornada abierta con visita abierta y pausa de comida activa
- **Datos de entrada:** subir foto y hacer check-out
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_P03_checkin_y_foto_bloqueados_en_pausa -v`
- **Resultado esperado:** HTTP 409 "Estás en pausa" en ambos
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Estás en pausa. Termina la pausa para continuar. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Estás en pausa. Termina la pausa para continuar. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_P03_checkin_y_foto_bloqueados_en_pausa(app, esc, obs):
    """P03 · No se registran check-in ni fotos durante una pausa
    RF: RF-08; regla C9 (estados incompatibles)
    Tipo: inválido
    Pre: jornada abierta con visita abierta y pausa de comida activa
    Entrada: subir foto y hacer check-out
    Esperado: HTTP 409 "Estás en pausa" en ambos
    """
    c = _p1(app)
    _iniciar(c, esc)
    idv = _checkin(c, esc).get_json()["visita"]["id_visita"]
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Comida"})
    r = obs(subir_foto(c, idv, "Precios", punto(esc.coords[0])))
    assert r.status_code == 409 and "pausa" in r.get_json()["error"]
    assert c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0])}).status_code == 409
```

</details>

### A01 · Promotor sin acceso a registros ajenos

- **Requisito / caso de uso:** RNF-16 Seguridad de la información
- **Tipo:** no autorizado (petición manipulada)
- **Precondiciones:** P1 con visita y foto; P3 es otro promotor
- **Datos de entrada:** P3 consulta la visita de P1, su foto, usa una asignación de P1 y llama a la supervisión
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_jornada.py::test_A01_promotor_no_accede_a_registros_ajenos -v`
- **Resultado esperado:** 404 en visita, foto y asignación; 403 en endpoints de supervisión
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 404 · Evidencia no encontrada. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 404 · Evidencia no encontrada. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_A01_promotor_no_accede_a_registros_ajenos(app, esc, obs):
    """A01 · Promotor sin acceso a registros ajenos
    RF: RNF-16 Seguridad de la información
    Tipo: no autorizado (petición manipulada)
    Pre: P1 con visita y foto; P3 es otro promotor
    Entrada: P3 consulta la visita de P1, su foto, usa una asignación de P1 y llama a la supervisión
    Esperado: 404 en visita, foto y asignación; 403 en endpoints de supervisión
    """
    c1 = _p1(app)
    _iniciar(c1, esc)
    asign = _asignaciones(c1)[1]["id_asignacion"]
    idv = _checkin(c1, esc).get_json()["visita"]["id_visita"]
    url = subir_foto(c1, idv, "Precios", punto(esc.coords[0])).get_json()["evidencia"]["url"]
    c3 = cliente(app, "p3@test.mx")
    assert c3.get(f"/api/promotor/visitas/{idv}").status_code == 404
    r = obs(c3.get(url))
    assert r.status_code == 404
    c3.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[2]))
    assert c3.post("/api/promotor/visitas/checkin", json={"id_asignacion": asign, **punto(esc.coords[1])}).status_code == 404
    assert c3.get("/api/supervision/mapa").status_code == 403
```

</details>

### O01 · Reintentos con el mismo identificador no duplican registros

- **Requisito / caso de uso:** RNF-08/RNF-09 sincronización; regla C9 (sin duplicados)
- **Tipo:** válido (idempotencia)
- **Precondiciones:** P1 con jornada iniciada
- **Datos de entrada:** el mismo check-in y la misma foto enviados 3 veces con igual X-Id-Cliente
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_O01_reintento_sin_duplicados -v`
- **Resultado esperado:** misma respuesta (201) marcada "repetido"; 1 visita y 1 evidencia en la base
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Foto guardada correctamente (Precios). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Foto guardada correctamente (Precios). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_O01_reintento_sin_duplicados(app, esc, obs):
    """O01 · Reintentos con el mismo identificador no duplican registros
    RF: RNF-08/RNF-09 sincronización; regla C9 (sin duplicados)
    Tipo: válido (idempotencia)
    Pre: P1 con jornada iniciada
    Entrada: el mismo check-in y la misma foto enviados 3 veces con igual X-Id-Cliente
    Esperado: misma respuesta (201) marcada "repetido"; 1 visita y 1 evidencia en la base
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    cab = {"X-Id-Cliente": str(uuid.uuid4())}
    cuerpos = [c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"],
                                                             **punto(esc.coords[0], 5)}, headers=cab) for _ in range(3)]
    assert [r.status_code for r in cuerpos] == [201, 201, 201]
    assert cuerpos[2].get_json()["repetido"] is True
    idv = cuerpos[0].get_json()["visita"]["id_visita"]
    cab_f = {"X-Id-Cliente": str(uuid.uuid4())}
    datos = b"\xff\xd8\xff\xe0" + b"x" * 300
    rs = [subir_foto(c, idv, "Precios", punto(esc.coords[0], 5), datos=datos, cabeceras=cab_f) for _ in range(3)]
    obs(rs[-1])
    assert [r.status_code for r in rs] == [201, 201, 201]
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Visita)).scalar_one() == 1
        assert db.session.execute(db.select(db.func.count()).select_from(Evidencia)).scalar_one() == 1
```

</details>

### O02 · Eventos sin conexión: se valida al sincronizar con la hora de captura

- **Requisito / caso de uso:** RNF-08 Funcionamiento sin conexión
- **Tipo:** válido
- **Precondiciones:** P1 sin señal desde las 08:05; llegan los eventos a las 10:00
- **Datos de entrada:** inicio 08:05, check-in 08:15 (X-Origen sin-conexion) y foto 08:20 que referencia el check-in por su ID de cliente
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_O02_sincronizacion_respeta_hora_de_captura -v`
- **Resultado esperado:** registros con hora de captura 08:05/08:15/08:20, recepción 10:00 y origen "Sin conexión"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Foto guardada correctamente (Precios). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Foto guardada correctamente (Precios). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_O02_sincronizacion_respeta_hora_de_captura(app, esc, obs):
    """O02 · Eventos sin conexión: se valida al sincronizar con la hora de captura
    RF: RNF-08 Funcionamiento sin conexión
    Tipo: válido
    Pre: P1 sin señal desde las 08:05; llegan los eventos a las 10:00
    Entrada: inicio 08:05, check-in 08:15 (X-Origen sin-conexion) y foto 08:20 que referencia el check-in por su ID de cliente
    Esperado: registros con hora de captura 08:05/08:15/08:20, recepción 10:00 y origen "Sin conexión"
    """
    c = cliente(app, "p1@test.mx")
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    a_las(10, 0)
    off = {"X-Origen": "sin-conexion"}
    r = c.post("/api/promotor/jornada/iniciar", json={**punto(esc.coords[0]), "capturado_en": "2026-11-04T08:05:00"},
               headers={**off, "X-Id-Cliente": str(uuid.uuid4())})
    assert r.status_code == 201
    id_ci = str(uuid.uuid4())
    r = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0]),
                                                      "capturado_en": "2026-11-04T08:15:00"},
               headers={**off, "X-Id-Cliente": id_ci})
    assert r.status_code == 201
    form_coord = punto(esc.coords[0])
    import io
    r = obs(c.post("/api/promotor/evidencias", data={
        "categoria": "Precios", "visita_cliente": id_ci, **{k: str(v) for k, v in form_coord.items()},
        "capturado_en": "2026-11-04T08:20:00", "foto": (io.BytesIO(b"\xff\xd8\xff" + b"z" * 50), "f.jpg")},
        content_type="multipart/form-data", headers={**off, "X-Id-Cliente": str(uuid.uuid4())}))
    assert r.status_code == 201
    with app.app_context():
        j = db.session.execute(db.select(Jornada)).scalar_one()
        v = db.session.execute(db.select(Visita)).scalar_one()
        e = db.session.execute(db.select(Evidencia)).scalar_one()
        assert j.fecha_hora_inicio == datetime(2026, 11, 4, 8, 5) and j.origen == "Sin conexión"
        assert v.fecha_hora_checkin == datetime(2026, 11, 4, 8, 15) and v.recepcion_checkin == datetime(2026, 11, 4, 10, 0)
        assert e.fecha_hora_captura == datetime(2026, 11, 4, 8, 20) and e.origen == "Sin conexión"
```

</details>

### O03 · Un evento sin conexión que viola una regla se rechaza al sincronizar

- **Requisito / caso de uso:** RNF-08; regla "una visita pendiente no se presenta como validada"
- **Tipo:** inválido
- **Precondiciones:** P1 sin jornada
- **Datos de entrada:** (a) check-in sin conexión fuera de geocerca tras iniciar; (b) hora de captura en el futuro
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_O03_evento_offline_invalido_se_rechaza -v`
- **Resultado esperado:** (a) 409 radio permitido; (b) 400 "hora del dispositivo está adelantada"
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 499 m y el radio es de 50 m. · {'distancia_m': 499.4} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No estás dentro del radio permitido de la tienda: estás a 499 m y el radio es de 50 m. · {'distancia_m': 499.4} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_O03_evento_offline_invalido_se_rechaza(app, esc, obs):
    """O03 · Un evento sin conexión que viola una regla se rechaza al sincronizar
    RF: RNF-08; regla "una visita pendiente no se presenta como validada"
    Tipo: inválido
    Pre: P1 sin jornada
    Entrada: (a) check-in sin conexión fuera de geocerca tras iniciar; (b) hora de captura en el futuro
    Esperado: (a) 409 radio permitido; (b) 400 "hora del dispositivo está adelantada"
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    r = obs(c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 500),
                                                          "capturado_en": "2026-11-04T08:06:00"},
                   headers={"X-Origen": "sin-conexion", "X-Id-Cliente": str(uuid.uuid4())}))
    assert r.status_code == 409
    r = c.post("/api/promotor/ubicaciones", json={**punto(esc.coords[0]), "capturado_en": "2026-11-04T09:30:00"})
    assert r.status_code == 400 and "adelantada" in r.get_json()["error"]
```

</details>

### O04 · Punto capturado durante una pausa que llega tarde por falta de señal

- **Requisito / caso de uso:** RF-02, RF-08, RNF-08
- **Tipo:** inválido
- **Precondiciones:** pausa de descanso de 09:00 a 09:20 ya terminada
- **Datos de entrada:** a las 09:30 llega una ubicación capturada a las 09:10
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_O04_ubicacion_capturada_en_pausa_no_se_guarda -v`
- **Resultado esperado:** HTTP 409 "suspendido durante la pausa"; no se guarda
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · El seguimiento está suspendido durante la pausa. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · El seguimiento está suspendido durante la pausa. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_O04_ubicacion_capturada_en_pausa_no_se_guarda(app, esc, obs):
    """O04 · Punto capturado durante una pausa que llega tarde por falta de señal
    RF: RF-02, RF-08, RNF-08
    Tipo: inválido
    Pre: pausa de descanso de 09:00 a 09:20 ya terminada
    Entrada: a las 09:30 llega una ubicación capturada a las 09:10
    Esperado: HTTP 409 "suspendido durante la pausa"; no se guarda
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a_las(9, 0)
    c.post("/api/promotor/pausas/iniciar", json={"tipo": "Descanso"})
    a_las(9, 20)
    c.post("/api/promotor/pausas/finalizar", json={})
    a_las(9, 30)
    r = obs(c.post("/api/promotor/ubicaciones", json={**punto(esc.coords[0], 200), "capturado_en": "2026-11-04T09:10:00"}))
    assert r.status_code == 409
    with app.app_context():
        assert db.session.execute(db.select(db.func.count()).select_from(Ubicacion)).scalar_one() == 1  # solo el inicio
```

</details>

### S01 · Mapa con última ubicación y estados separados, limitado al ámbito

- **Requisito / caso de uso:** RF-10 Mapa en tiempo real; RF-02; estados de cuenta, jornada, visita y conexión
- **Tipo:** válido / alcance
- **Precondiciones:** P1 en tienda (visita abierta); P2 sin jornada; P3 pertenece a S2
- **Datos de entrada:** S1 consulta /api/supervision/mapa; admin consulta el mismo
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_S01_mapa_y_alcance_supervisor -v`
- **Resultado esperado:** S1 ve P1 y P2 (no P3), P1 "En tienda" con ubicación reciente; admin ve a los 3
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Historial:** falló antes de la corrección F04 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_S01_mapa_y_alcance_supervisor(app, esc, obs):
    """S01 · Mapa con última ubicación y estados separados, limitado al ámbito
    RF: RF-10 Mapa en tiempo real; RF-02; estados de cuenta, jornada, visita y conexión
    Tipo: válido / alcance
    Pre: P1 en tienda (visita abierta); P2 sin jornada; P3 pertenece a S2
    Entrada: S1 consulta /api/supervision/mapa; admin consulta el mismo
    Esperado: S1 ve P1 y P2 (no P3), P1 "En tienda" con ubicación reciente; admin ve a los 3
    """
    _jornada_con_visita(app, esc, cerrar=False)
    r = obs(cliente(app, "s1@test.mx").get("/api/supervision/mapa"))
    ps = {p["numero_empleado"]: p for p in r.get_json()["promotores"]}
    assert set(ps) == {"P1", "P2"}
    p1 = ps["P1"]
    assert (p1["estado_cuenta"], p1["estado_jornada"], p1["estado_visita"], p1["estado_conexion"]) == \
           ("Activo", "En jornada", "En tienda", "Reciente")
    assert p1["ultima_ubicacion"]["fecha_hora"].startswith("2026-11-04T08:05")
    assert ps["P2"]["estado_jornada"] == "Sin jornada"
    admin = cliente(app, "admin@test.mx").get("/api/supervision/mapa").get_json()
    # Corrección F04: los datos base de la etapa 1 incluyen a "Pedro
    # Promotor" (activo, sin número de empleado); el administrador también
    # lo ve. Se verifica que vea a todos los promotores activos.
    assert {p["nombre_completo"] for p in admin["promotores"]} == {
        "Marco Promotor", "Julieta Promotora", "Pablo Promotor", "Pedro Promotor"}
```

</details>

### S02 · Diferenciar ubicación reciente de desactualizada

- **Requisito / caso de uso:** RF-10; excepción del modelo de diseño (promotor sin señal se muestra como desconectado)
- **Tipo:** válido
- **Precondiciones:** P1 inició a las 08:05 y no envía ubicaciones; parámetro ubicacion_reciente_min = 20
- **Datos de entrada:** S1 consulta el mapa a las 08:20 y a las 08:40
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_S02_ubicacion_desactualizada -v`
- **Resultado esperado:** 08:20 "Reciente"; 08:40 "Desactualizada" y cuenta como desconectado
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Historial:** falló antes de la corrección F05 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_S02_ubicacion_desactualizada(app, esc, obs):
    """S02 · Diferenciar ubicación reciente de desactualizada
    RF: RF-10; excepción del modelo de diseño (promotor sin señal se muestra como desconectado)
    Tipo: válido
    Pre: P1 inició a las 08:05 y no envía ubicaciones; parámetro ubicacion_reciente_min = 20
    Entrada: S1 consulta el mapa a las 08:20 y a las 08:40
    Esperado: 08:20 "Reciente"; 08:40 "Desactualizada" y cuenta como desconectado
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    s1 = cliente(app, "s1@test.mx")
    a_las(8, 20)
    # Corrección F05: la lista viene ordenada por nombre (Julieta antes que
    # Marco); se busca a P1 por su número en lugar de tomar la posición 0.
    p1 = [p for p in s1.get("/api/supervision/mapa").get_json()["promotores"] if p["numero_empleado"] == "P1"][0]
    assert p1["estado_conexion"] == "Reciente"
    a_las(8, 40)
    r = obs(s1.get("/api/supervision/mapa"))
    p1 = [p for p in r.get_json()["promotores"] if p["numero_empleado"] == "P1"][0]
    assert p1["estado_conexion"] == "Desactualizada" and r.get_json()["resumen"]["Desconectados"] == 1
```

</details>

### I01 · Alerta crítica: no llegó a su primera tienda

- **Requisito / caso de uso:** RF-11 Alertas automáticas (30 min); canal: notificación interna del panel
- **Tipo:** válido (alerta)
- **Precondiciones:** P1 tiene asignaciones y no inicia jornada; P3 tampoco (pertenece a S2)
- **Datos de entrada:** S1 consulta el mapa a las 08:25 y a las 08:31
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_I01_alerta_sin_llegada -v`
- **Resultado esperado:** 08:25 sin alerta; 08:31 una alerta crítica para P1, sin duplicarse al volver a consultar
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_I01_alerta_sin_llegada(app, esc, obs):
    """I01 · Alerta crítica: no llegó a su primera tienda
    RF: RF-11 Alertas automáticas (30 min); canal: notificación interna del panel
    Tipo: válido (alerta)
    Pre: P1 tiene asignaciones y no inicia jornada; P3 tampoco (pertenece a S2)
    Entrada: S1 consulta el mapa a las 08:25 y a las 08:31
    Esperado: 08:25 sin alerta; 08:31 una alerta crítica para P1, sin duplicarse al volver a consultar
    """
    s1 = cliente(app, "s1@test.mx")
    a_las(8, 25)
    assert s1.get("/api/supervision/mapa").get_json()["alertas"] == []
    a_las(8, 31)
    s1.get("/api/supervision/mapa")
    r = obs(s1.get("/api/supervision/mapa"))
    al = r.get_json()["alertas"]
    assert len(al) == 1 and al[0]["tipo"] == "Sin llegada a primera tienda" and al[0]["nombre_promotor"] == "Marco Promotor"
```

</details>

### I02 · Inactividad: alerta fuera de tienda, no dentro de una visita larga

- **Requisito / caso de uso:** RF-11 (2 horas sin moverse) con la observación de la entrevista (tiendas de 5 horas)
- **Tipo:** válido
- **Precondiciones:** P1 con visita abierta 08:10-11:00 (sin moverse); luego fuera de tienda sin moverse 11:00-13:05
- **Datos de entrada:** S1 consulta el mapa a las 11:00 (en tienda) y a las 13:05 (fuera de tienda)
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_I02_inactividad_fuera_de_tienda_y_no_dentro -v`
- **Resultado esperado:** sin alerta de inactividad durante la visita; alerta crítica "Inactividad" a las 13:05
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_I02_inactividad_fuera_de_tienda_y_no_dentro(app, esc, obs):
    """I02 · Inactividad: alerta fuera de tienda, no dentro de una visita larga
    RF: RF-11 (2 horas sin moverse) con la observación de la entrevista (tiendas de 5 horas)
    Tipo: válido
    Pre: P1 con visita abierta 08:10-11:00 (sin moverse); luego fuera de tienda sin moverse 11:00-13:05
    Entrada: S1 consulta el mapa a las 11:00 (en tienda) y a las 13:05 (fuera de tienda)
    Esperado: sin alerta de inactividad durante la visita; alerta crítica "Inactividad" a las 13:05
    """
    c, idv = _jornada_con_visita(app, esc, cerrar=False)
    s1 = cliente(app, "s1@test.mx")
    for h in (9, 10, 11):
        a_las(h, 0)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 5))
    assert not [a for a in s1.get("/api/supervision/mapa").get_json()["alertas"] if a["tipo"] == "Inactividad"]
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    for h, m in ((11, 30), (12, 0), (12, 30), (13, 0)):
        a_las(h, m)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[0], 400))
    a_las(13, 5)
    r = obs(s1.get("/api/supervision/mapa"))
    assert [a["tipo"] for a in r.get_json()["alertas"]].count("Inactividad") == 1
```

</details>

### I03 · Historial de incidencias por promotor y seguimiento manual

- **Requisito / caso de uso:** RF-18 Ver historial de incidencias; diccionario INCIDENCIA (Pendiente/Revisada/Sancionada)
- **Tipo:** válido / alcance
- **Precondiciones:** P1 con una foto fuera de geocerca (incidencia crítica)
- **Datos de entrada:** S1 lista incidencias de P1 y la marca como Revisada; S2 intenta modificarla
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_I03_seguimiento_de_incidencias -v`
- **Resultado esperado:** S1 ve 1 incidencia y la actualiza (200); S2 recibe 404
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Incidencia actualizada. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Incidencia actualizada. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_I03_seguimiento_de_incidencias(app, esc, obs):
    """I03 · Historial de incidencias por promotor y seguimiento manual
    RF: RF-18 Ver historial de incidencias; diccionario INCIDENCIA (Pendiente/Revisada/Sancionada)
    Tipo: válido / alcance
    Pre: P1 con una foto fuera de geocerca (incidencia crítica)
    Entrada: S1 lista incidencias de P1 y la marca como Revisada; S2 intenta modificarla
    Esperado: S1 ve 1 incidencia y la actualiza (200); S2 recibe 404
    """
    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0]))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin", json={"id_asignacion": a["id_asignacion"],
                                                        **punto(esc.coords[0])}).get_json()["visita"]["id_visita"]
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 500))
    s1 = cliente(app, "s1@test.mx")
    lista = s1.get(f"/api/incidencias?id_promotor={esc.ids.p1}").get_json()["incidencias"]
    assert len(lista) == 1 and lista[0]["es_critica"]
    r = obs(s1.put(f"/api/incidencias/{lista[0]['id_incidencia']}", json={"estado": "Revisada", "comentario": "Se habló con el promotor"}))
    assert r.status_code == 200 and r.get_json()["incidencia"]["estado"] == "Revisada"
    assert cliente(app, "s2@test.mx").put(f"/api/incidencias/{lista[0]['id_incidencia']}",
                                          json={"estado": "Sancionada"}).status_code == 404
```

</details>

### S03 · Historial de ubicaciones y consulta de visitas con evidencias

- **Requisito / caso de uso:** RF-14 Historial de ubicaciones; RF-07/2.2 revisión de evidencias
- **Tipo:** válido / alcance
- **Precondiciones:** P1 con jornada, 2 ubicaciones adicionales y una visita cerrada con 4 fotos
- **Datos de entrada:** S1 consulta seguimiento y visitas de P1; S2 consulta el seguimiento de P1
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_S03_historial_ubicaciones_y_evidencias -v`
- **Resultado esperado:** 3 puntos en orden cronológico; 1 visita con 4 evidencias válidas; S2 recibe 404
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_S03_historial_ubicaciones_y_evidencias(app, esc, obs):
    """S03 · Historial de ubicaciones y consulta de visitas con evidencias
    RF: RF-14 Historial de ubicaciones; RF-07/2.2 revisión de evidencias
    Tipo: válido / alcance
    Pre: P1 con jornada, 2 ubicaciones adicionales y una visita cerrada con 4 fotos
    Entrada: S1 consulta seguimiento y visitas de P1; S2 consulta el seguimiento de P1
    Esperado: 3 puntos en orden cronológico; 1 visita con 4 evidencias válidas; S2 recibe 404
    """
    c, _ = _jornada_con_visita(app, esc)
    for h in (10, 11):
        a_las(h, 0)
        c.post("/api/promotor/ubicaciones", json=punto(esc.coords[1], h * 10))
    s1 = cliente(app, "s1@test.mx")
    r = obs(s1.get(f"/api/supervision/seguimiento?id_promotor={esc.ids.p1}&fecha=2026-11-04"))
    horas = [u["fecha_hora"][11:16] for u in r.get_json()["ubicaciones"]]
    assert horas == ["08:05", "10:00", "11:00"]
    vs = s1.get(f"/api/supervision/visitas?id_promotor={esc.ids.p1}&desde=2026-11-04").get_json()["visitas"]
    assert len(vs) == 1 and len([e for e in vs[0]["evidencias"] if e["estatus_validacion"] == "Válida"]) == 4
    assert cliente(app, "s2@test.mx").get(f"/api/supervision/seguimiento?id_promotor={esc.ids.p1}").status_code == 404
```

</details>

### REP01 · Reporte diario de desempeño consistente con los registros

- **Requisito / caso de uso:** RF-13, RF-15 Reportes de desempeño
- **Tipo:** válido
- **Precondiciones:** P1 con 2 asignadas, 1 visitada (08:10-09:40), 1 foto fuera de geocerca adicional; jornada iniciada 08:05
- **Datos de entrada:** S1 genera reporte Diario de Desempeño para P1 el 4-nov-2026
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_REP01_reporte_consistente_con_registros -v`
- **Resultado esperado:** asignadas 2, visitadas 1, cumplimiento 50 %, tiempo promedio 90 min, fotos válidas 4 de 5, incidencias 1 crítica
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Reporte generado. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Reporte generado. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_REP01_reporte_consistente_con_registros(app, esc, obs):
    """REP01 · Reporte diario de desempeño consistente con los registros
    RF: RF-13, RF-15 Reportes de desempeño
    Tipo: válido
    Pre: P1 con 2 asignadas, 1 visitada (08:10-09:40), 1 foto fuera de geocerca adicional; jornada iniciada 08:05
    Entrada: S1 genera reporte Diario de Desempeño para P1 el 4-nov-2026
    Esperado: asignadas 2, visitadas 1, cumplimiento 50 %, tiempo promedio 90 min, fotos válidas 4 de 5, incidencias 1 crítica
    """
    c, idv = _jornada_con_visita(app, esc, cerrar=False)
    subir_foto(c, idv, "Precios", punto(esc.coords[0], 500))
    a_las(9, 40)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    r = obs(cliente(app, "s1@test.mx").post("/api/reportes", json={"tipo": "Diario", "contenido": "Desempeño",
                                                                    "fecha": "2026-11-04", "id_promotor": esc.ids.p1}))
    assert r.status_code == 201
    m = r.get_json()["metricas"]["promotores"][0]
    assert (m["tiendas_asignadas"], m["tiendas_visitadas"], m["cumplimiento_pct"]) == (2, 1, 50.0)
    assert m["tiempo_promedio_tienda_min"] == 90 and (m["fotos_validas"], m["fotos_total"]) == (4, 5)
    with app.app_context():
        assert m["incidencias_total"] == db.session.execute(db.select(db.func.count()).select_from(Incidencia).where(
            Incidencia.id_promotor == esc.ids.p1)).scalar_one() == 1
```

</details>

### REP02 · Exportar reporte de exhibición a PDF con evidencias y permisos

- **Requisito / caso de uso:** RF-16 Exportar reportes (PDF); entrevista P26 (imágenes de anaquel, precios y promociones)
- **Tipo:** válido / no autorizado
- **Precondiciones:** P1 con visita cerrada y 4 fotos (imágenes de prueba no decodificables)
- **Datos de entrada:** S1 genera reporte Semanal de Exhibición y descarga el PDF; S2 intenta descargarlo; S1 pide reporte de P3
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_REP02_pdf_y_permisos -v`
- **Resultado esperado:** PDF válido (%PDF); S2 recibe 404; reporte de P3 → 404
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Reporte generado. · PDF: HTTP 200, 3345 bytes, tipo application/pdf → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Reporte generado. · PDF: HTTP 200, 3345 bytes, tipo application/pdf → **EXITOSA**
- **Historial:** falló antes de la corrección F06 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_REP02_pdf_y_permisos(app, esc, obs):
    """REP02 · Exportar reporte de exhibición a PDF con evidencias y permisos
    RF: RF-16 Exportar reportes (PDF); entrevista P26 (imágenes de anaquel, precios y promociones)
    Tipo: válido / no autorizado
    Pre: P1 con visita cerrada y 4 fotos (imágenes de prueba no decodificables)
    Entrada: S1 genera reporte Semanal de Exhibición y descarga el PDF; S2 intenta descargarlo; S1 pide reporte de P3
    Esperado: PDF válido (%PDF); S2 recibe 404; reporte de P3 → 404
    """
    _jornada_con_visita(app, esc)
    s1 = cliente(app, "s1@test.mx")
    r = s1.post("/api/reportes", json={"tipo": "Semanal", "contenido": "Exhibición", "fecha": "2026-11-04"})
    assert r.status_code == 201 and r.get_json()["metricas"]["desde"] == "2026-11-02"
    idr = r.get_json()["reporte"]["id_reporte"]
    pdf = s1.get(f"/api/reportes/{idr}/pdf")
    obs(r, extra=f"PDF: HTTP {pdf.status_code}, {len(pdf.data)} bytes, tipo {pdf.mimetype}")
    assert pdf.status_code == 200 and pdf.data[:4] == b"%PDF" and pdf.mimetype == "application/pdf"
    assert cliente(app, "s2@test.mx").get(f"/api/reportes/{idr}/pdf").status_code == 404
    assert s1.post("/api/reportes", json={"tipo": "Diario", "fecha": "2026-11-04",
                                          "id_promotor": esc.ids.p3}).status_code == 404
```

</details>

### REP03 · Reporte sin datos en el periodo

- **Requisito / caso de uso:** RF-13 (excepción "No hay datos suficientes para generar el reporte")
- **Tipo:** inválido
- **Precondiciones:** no hay registros en marzo de 2026
- **Datos de entrada:** reporte Mensual con fecha 2026-03-15
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_REP03_sin_datos -v`
- **Resultado esperado:** HTTP 404 con el mensaje del modelo de diseño
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 404 · No hay datos suficientes para generar el reporte. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 404 · No hay datos suficientes para generar el reporte. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_REP03_sin_datos(app, esc, obs):
    """REP03 · Reporte sin datos en el periodo
    RF: RF-13 (excepción "No hay datos suficientes para generar el reporte")
    Tipo: inválido
    Pre: no hay registros en marzo de 2026
    Entrada: reporte Mensual con fecha 2026-03-15
    Esperado: HTTP 404 con el mensaje del modelo de diseño
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/reportes", json={"tipo": "Mensual", "fecha": "2026-03-15"}))
    assert r.status_code == 404 and r.get_json()["error"] == "No hay datos suficientes para generar el reporte."
```

</details>

### REP04 · El PDF de exhibición incrusta las fotografías válidas

- **Requisito / caso de uso:** RF-16; entrevista P26 (reportes con imágenes de exhibición, precios y promociones)
- **Tipo:** válido
- **Precondiciones:** visita cerrada con 4 fotos JPEG reales generadas con Pillow
- **Datos de entrada:** reporte Diario de Exhibición y descarga del PDF
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_supervision_reportes.py::test_REP04_pdf_incluye_fotos_reales -v`
- **Resultado esperado:** PDF con 4 imágenes incrustadas (objetos /Image)
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  · 7891 bytes, 4 imágenes incrustadas → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  · 7892 bytes, 4 imágenes incrustadas → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_REP04_pdf_incluye_fotos_reales(app, esc, obs):
    """REP04 · El PDF de exhibición incrusta las fotografías válidas
    RF: RF-16; entrevista P26 (reportes con imágenes de exhibición, precios y promociones)
    Tipo: válido
    Pre: visita cerrada con 4 fotos JPEG reales generadas con Pillow
    Entrada: reporte Diario de Exhibición y descarga del PDF
    Esperado: PDF con 4 imágenes incrustadas (objetos /Image)
    """
    import io as _io

    import pytest
    PIL = pytest.importorskip("PIL.Image")

    def jpeg(color):
        b = _io.BytesIO()
        PIL.new("RGB", (64, 48), color).save(b, "JPEG")
        return b.getvalue()

    c = cliente(app, "p1@test.mx")
    c.post("/api/promotor/jornada/iniciar", json=punto(esc.coords[0], 10))
    a = c.get("/api/promotor/hoy").get_json()["asignaciones"][0]
    idv = c.post("/api/promotor/visitas/checkin",
                 json={"id_asignacion": a["id_asignacion"], **punto(esc.coords[0], 5)}).get_json()["visita"]["id_visita"]
    for cat, color in zip(CATS, ("red", "green", "blue", "yellow")):
        assert subir_foto(c, idv, cat, punto(esc.coords[0], 5), datos=jpeg(color)).status_code == 201
    a_las(9, 0)
    c.post("/api/promotor/visitas/checkout", json={"id_visita": idv, **punto(esc.coords[0], 5)})
    s1 = cliente(app, "s1@test.mx")
    idr = s1.post("/api/reportes", json={"tipo": "Diario", "contenido": "Exhibición",
                                         "fecha": "2026-11-04"}).get_json()["reporte"]["id_reporte"]
    pdf = s1.get(f"/api/reportes/{idr}/pdf")
    imagenes = pdf.data.count(b"/Subtype /Image")
    obs(pdf, extra=f"{len(pdf.data)} bytes, {imagenes} imágenes incrustadas")
    assert pdf.status_code == 200 and imagenes == 4
```

</details>

### T01 · Registrar tienda con coordenadas, radio y tiempo estimado

- **Requisito / caso de uso:** RF-19 Agregar tiendas
- **Tipo:** válido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** Office Max Las Torres, lat 21.0950, lon -101.6400, radio 60 m, 90 min
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T01_alta_tienda_valida -v`
- **Resultado esperado:** HTTP 201 "Tienda registrada correctamente", estatus Activa
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Tienda registrada correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Tienda registrada correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T01_alta_tienda_valida(app, esc, obs):
    """T01 · Registrar tienda con coordenadas, radio y tiempo estimado
    RF: RF-19 Agregar tiendas
    Tipo: válido
    Pre: sesión de Administrador
    Entrada: Office Max Las Torres, lat 21.0950, lon -101.6400, radio 60 m, 90 min
    Esperado: HTTP 201 "Tienda registrada correctamente", estatus Activa
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/tiendas", json=TIENDA))
    assert r.status_code == 201 and r.get_json()["tienda"]["estatus"] == "Activa"
    assert r.get_json()["tienda"]["radio_geocerca_m"] == 60
```

</details>

### T02 · Tienda sin coordenadas y con radio fuera de rango

- **Requisito / caso de uso:** RF-19; excepción del modelo de diseño ("Las coordenadas GPS son obligatorias...")
- **Tipo:** inválido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** latitud vacía, longitud 500, radio 5 m
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T02_coordenadas_obligatorias -v`
- **Resultado esperado:** HTTP 400 con mensaje en latitud, longitud y radio
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · Revisa los campos marcados. · {'campos': {'latitud': 'Las coordenadas GPS son obligatorias para el cálculo de la geocerca.', 'longitud': 'Debe estar entre -180 y 180.', 'radio_geocerca_m': 'El radio debe ser un número entre 10 y 1000 metros.'}} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · Revisa los campos marcados. · {'campos': {'latitud': 'Las coordenadas GPS son obligatorias para el cálculo de la geocerca.', 'longitud': 'Debe estar entre -180 y 180.', 'radio_geocerca_m': 'El radio debe ser un número entre 10 y 1000 metros.'}} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T02_coordenadas_obligatorias(app, esc, obs):
    """T02 · Tienda sin coordenadas y con radio fuera de rango
    RF: RF-19; excepción del modelo de diseño ("Las coordenadas GPS son obligatorias...")
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: latitud vacía, longitud 500, radio 5 m
    Esperado: HTTP 400 con mensaje en latitud, longitud y radio
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/tiendas", json={**TIENDA, "latitud": "", "longitud": "500",
                                                                      "radio_geocerca_m": 5}))
    assert r.status_code == 400
    campos = r.get_json()["campos"]
    assert "obligatorias" in campos["latitud"] and "longitud" in campos and "radio_geocerca_m" in campos
```

</details>

### T03 · Listado de tiendas con filtros por cadena, zona y estado

- **Requisito / caso de uso:** RF-20 Consultar/Ver listado de tiendas
- **Tipo:** válido
- **Precondiciones:** 4 tiendas (2 de cadena Walmart; 3 en zona Norte)
- **Datos de entrada:** ?cadena=Walmart y ?zona=Norte&estatus=Activa y ?q=soriana
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T03_filtros_listado -v`
- **Resultado esperado:** 2, 3 y 1 resultados respectivamente
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T03_filtros_listado(app, esc, obs):
    """T03 · Listado de tiendas con filtros por cadena, zona y estado
    RF: RF-20 Consultar/Ver listado de tiendas
    Tipo: válido
    Pre: 4 tiendas (2 de cadena Walmart; 3 en zona Norte)
    Entrada: ?cadena=Walmart y ?zona=Norte&estatus=Activa y ?q=soriana
    Esperado: 2, 3 y 1 resultados respectivamente
    """
    c = cliente(app, "s1@test.mx")
    assert c.get("/api/tiendas?cadena=Walmart").get_json()["total"] == 2
    assert c.get("/api/tiendas?zona=Norte&estatus=Activa").get_json()["total"] == 3
    r = obs(c.get("/api/tiendas?q=soriana"))
    assert r.get_json()["total"] == 1
```

</details>

### T04 · No se desactiva una tienda con visitas programadas

- **Requisito / caso de uso:** RF-21 Eliminar/Desactivar tiendas (excepción del modelo de diseño)
- **Tipo:** inválido (estado incompatible)
- **Precondiciones:** Walmart Torres Landa asignada hoy a P1 sin visita
- **Datos de entrada:** POST /api/tiendas/{Walmart}/desactivar
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T04_no_desactivar_tienda_programada -v`
- **Resultado esperado:** HTTP 409 "No se puede desactivar porque está asignada..."
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No se puede desactivar porque está asignada a una ruta activa o tiene visitas programadas. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No se puede desactivar porque está asignada a una ruta activa o tiene visitas programadas. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T04_no_desactivar_tienda_programada(app, esc, obs):
    """T04 · No se desactiva una tienda con visitas programadas
    RF: RF-21 Eliminar/Desactivar tiendas (excepción del modelo de diseño)
    Tipo: inválido (estado incompatible)
    Pre: Walmart Torres Landa asignada hoy a P1 sin visita
    Entrada: POST /api/tiendas/{Walmart}/desactivar
    Esperado: HTTP 409 "No se puede desactivar porque está asignada..."
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/tiendas/{esc.ids.t[0]}/desactivar"))
    assert r.status_code == 409 and r.get_json()["asignaciones_pendientes"] == 1
```

</details>

### T05 · Baja lógica de una tienda sin asignaciones y exclusión de futuras rutas

- **Requisito / caso de uso:** RF-21
- **Tipo:** válido
- **Precondiciones:** Bodega Aurrera sin asignaciones
- **Datos de entrada:** desactivar y luego intentar asignarla a P2 para mañana
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T05_baja_logica_tienda -v`
- **Resultado esperado:** 200 al desactivar (registro conservado); 400 al asignarla ("tiendas inactivas")
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Tienda desactivada correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Tienda desactivada correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T05_baja_logica_tienda(app, esc, obs):
    """T05 · Baja lógica de una tienda sin asignaciones y exclusión de futuras rutas
    RF: RF-21
    Tipo: válido
    Pre: Bodega Aurrera sin asignaciones
    Entrada: desactivar y luego intentar asignarla a P2 para mañana
    Esperado: 200 al desactivar (registro conservado); 400 al asignarla ("tiendas inactivas")
    """
    admin = cliente(app, "admin@test.mx")
    r = obs(admin.post(f"/api/tiendas/{esc.ids.t[3]}/desactivar"))
    assert r.status_code == 200 and r.get_json()["tienda"]["estatus"] == "Inactiva"
    r = cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p2, "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[3]]})
    assert r.status_code == 400 and "inactivas" in r.get_json()["error"]
```

</details>

### T06 · Supervisor no puede crear ni editar tiendas

- **Requisito / caso de uso:** RF-19 (actor Administrador); RNF-16
- **Tipo:** no autorizado
- **Precondiciones:** sesión de Supervisor S1
- **Datos de entrada:** POST /api/tiendas
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_T06_tiendas_solo_admin_escribe -v`
- **Resultado esperado:** HTTP 403
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 403 · No tienes permiso para esta sección. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 403 · No tienes permiso para esta sección. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_T06_tiendas_solo_admin_escribe(app, esc, obs):
    """T06 · Supervisor no puede crear ni editar tiendas
    RF: RF-19 (actor Administrador); RNF-16
    Tipo: no autorizado
    Pre: sesión de Supervisor S1
    Entrada: POST /api/tiendas
    Esperado: HTTP 403
    """
    r = obs(cliente(app, "s1@test.mx").post("/api/tiendas", json=TIENDA))
    assert r.status_code == 403
```

</details>

### R01 · Asignar tiendas por fecha y orden conservando historial

- **Requisito / caso de uso:** RF-09 Asignación y gestión de rutas
- **Tipo:** válido
- **Precondiciones:** P1 tiene mañana sin asignaciones
- **Datos de entrada:** asignar [Office Depot, Soriana, Walmart]; luego cambiar a [Walmart, Soriana]
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R01_asignar_dia_con_historial -v`
- **Resultado esperado:** 3 asignaciones activas con orden 1-2-3; después Office Depot queda Cancelada y el orden es 1-2
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Asignación guardada correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Asignación guardada correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R01_asignar_dia_con_historial(app, esc, obs):
    """R01 · Asignar tiendas por fecha y orden conservando historial
    RF: RF-09 Asignación y gestión de rutas
    Tipo: válido
    Pre: P1 tiene mañana sin asignaciones
    Entrada: asignar [Office Depot, Soriana, Walmart]; luego cambiar a [Walmart, Soriana]
    Esperado: 3 asignaciones activas con orden 1-2-3; después Office Depot queda Cancelada y el orden es 1-2
    """
    c = cliente(app, "s1@test.mx")
    manana = (HOY + timedelta(days=1)).isoformat()
    t = esc.ids.t
    assert c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p1, "fecha": manana,
                                                "tiendas": [t[2], t[1], t[0]]}).status_code == 200
    r = obs(c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p1, "fecha": manana, "tiendas": [t[0], t[1]]}))
    assert r.status_code == 200
    activas = c.get(f"/api/asignaciones?id_promotor={esc.ids.p1}&fecha={manana}").get_json()["asignaciones"]
    assert [(a["tienda"]["id_tienda"], a["orden_visita"]) for a in activas] == [(t[0], 1), (t[1], 2)]
    todas = c.get(f"/api/asignaciones?id_promotor={esc.ids.p1}&fecha={manana}&historial=1").get_json()["asignaciones"]
    assert [a["estado"] for a in todas if a["tienda"]["id_tienda"] == t[2]] == ["Cancelada"]
```

</details>

### R02 · Cantidad de tiendas fuera de 3-4 genera advertencia, no bloqueo

- **Requisito / caso de uso:** RF-09 (3 a 4 tiendas) frente a entrevista P10 (tiendas de 5 horas)
- **Tipo:** válido (regla flexible)
- **Precondiciones:** sesión de S1
- **Datos de entrada:** asignar 1 sola tienda a P2 para mañana
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R02_cantidad_sugerida_no_bloquea -v`
- **Resultado esperado:** HTTP 200 con advertencia sobre la cantidad sugerida
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Asignación guardada correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Asignación guardada correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R02_cantidad_sugerida_no_bloquea(app, esc, obs):
    """R02 · Cantidad de tiendas fuera de 3-4 genera advertencia, no bloqueo
    RF: RF-09 (3 a 4 tiendas) frente a entrevista P10 (tiendas de 5 horas)
    Tipo: válido (regla flexible)
    Pre: sesión de S1
    Entrada: asignar 1 sola tienda a P2 para mañana
    Esperado: HTTP 200 con advertencia sobre la cantidad sugerida
    """
    r = obs(cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p2, "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 200 and any("sugieren" in a for a in r.get_json()["advertencias"])
```

</details>

### R03 · Supervisor no puede asignar ni consultar promotores ajenos

- **Requisito / caso de uso:** RF-09; RNF-16 (supervisor limitado a su ámbito)
- **Tipo:** no autorizado (petición manipulada)
- **Precondiciones:** P3 pertenece a S2
- **Datos de entrada:** S1 envía PUT /api/asignaciones/dia y GET /api/asignaciones para P3
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R03_supervisor_fuera_de_alcance -v`
- **Resultado esperado:** HTTP 404 en ambos; no se crean asignaciones
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 404 · Promotor no encontrado o fuera de tu alcance. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 404 · Promotor no encontrado o fuera de tu alcance. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R03_supervisor_fuera_de_alcance(app, esc, obs):
    """R03 · Supervisor no puede asignar ni consultar promotores ajenos
    RF: RF-09; RNF-16 (supervisor limitado a su ámbito)
    Tipo: no autorizado (petición manipulada)
    Pre: P3 pertenece a S2
    Entrada: S1 envía PUT /api/asignaciones/dia y GET /api/asignaciones para P3
    Esperado: HTTP 404 en ambos; no se crean asignaciones
    """
    c = cliente(app, "s1@test.mx")
    r = obs(c.put("/api/asignaciones/dia", json={"id_promotor": esc.ids.p3,
                                                 "fecha": (HOY + timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 404
    assert c.get(f"/api/asignaciones?id_promotor={esc.ids.p3}&fecha={HOY}").status_code == 404
```

</details>

### R04 · Las asignaciones de días pasados no se modifican

- **Requisito / caso de uso:** RF-09 (historial)
- **Tipo:** inválido
- **Precondiciones:** hoy es 4-nov-2026
- **Datos de entrada:** guardar asignación para el 3-nov-2026
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R04_no_modificar_dias_pasados -v`
- **Resultado esperado:** HTTP 409
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · No se pueden modificar asignaciones de días pasados; se conservan como historial. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · No se pueden modificar asignaciones de días pasados; se conservan como historial. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R04_no_modificar_dias_pasados(app, esc, obs):
    """R04 · Las asignaciones de días pasados no se modifican
    RF: RF-09 (historial)
    Tipo: inválido
    Pre: hoy es 4-nov-2026
    Entrada: guardar asignación para el 3-nov-2026
    Esperado: HTTP 409
    """
    r = obs(cliente(app, "s1@test.mx").put("/api/asignaciones/dia", json={
        "id_promotor": esc.ids.p1, "fecha": (HOY - timedelta(days=1)).isoformat(), "tiendas": [esc.ids.t[0]]}))
    assert r.status_code == 409
```

</details>

### R05 · Crear ruta (plantilla) y aplicarla a un rango de fechas

- **Requisito / caso de uso:** RF-09; prototipo admin "Crear una ruta" (nombre, promotor, días, tiendas)
- **Tipo:** válido
- **Precondiciones:** P2 sin asignaciones
- **Datos de entrada:** ruta "Zona Norte" LUN-MIE-VIE con 3 tiendas; aplicar del 9 al 15 de nov (lun a dom)
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R05_ruta_plantilla_y_aplicar -v`
- **Resultado esperado:** ruta Activa; 3 días creados (9, 11 y 13), 3 asignaciones por día con orden 1-3
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Ruta aplicada a 3 día(s). → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Ruta aplicada a 3 día(s). → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R05_ruta_plantilla_y_aplicar(app, esc, obs):
    """R05 · Crear ruta (plantilla) y aplicarla a un rango de fechas
    RF: RF-09; prototipo admin "Crear una ruta" (nombre, promotor, días, tiendas)
    Tipo: válido
    Pre: P2 sin asignaciones
    Entrada: ruta "Zona Norte" LUN-MIE-VIE con 3 tiendas; aplicar del 9 al 15 de nov (lun a dom)
    Esperado: ruta Activa; 3 días creados (9, 11 y 13), 3 asignaciones por día con orden 1-3
    """
    c = cliente(app, "admin@test.mx")
    t = esc.ids.t
    r = c.post("/api/rutas", json={"nombre_ruta": "Zona Norte", "id_promotor": esc.ids.p2,
                                   "dias_programados": ["LUN", "MIE", "VIE"], "tiendas": [t[0], t[1], t[2]]})
    assert r.status_code == 201
    idr = r.get_json()["ruta"]["id_ruta"]
    r = obs(c.post(f"/api/rutas/{idr}/aplicar", json={"desde": "2026-11-09", "hasta": "2026-11-15"}))
    assert r.get_json()["dias_creados"] == 3
    with app.app_context():
        filas = db.session.execute(db.select(Asignacion.fecha, Asignacion.orden_visita).where(
            Asignacion.id_promotor == esc.ids.p2).order_by(Asignacion.fecha, Asignacion.orden_visita)).all()
        assert len(filas) == 9 and {f[0].day for f in filas} == {9, 11, 13}
```

</details>

### R06 · Ruta sin días ni tiendas

- **Requisito / caso de uso:** RF-09; RF-23 mensajes de error
- **Tipo:** inválido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** nombre vacío, días [], tiendas []
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_tiendas_rutas.py::test_R06_ruta_sin_dias_ni_tiendas -v`
- **Resultado esperado:** HTTP 400 con mensajes en nombre_ruta, dias_programados y tiendas
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · Revisa los campos marcados. · {'campos': {'dias_programados': 'Selecciona al menos un día de visita.', 'nombre_ruta': 'El nombre de la ruta es obligatorio (máximo 100 caracteres).', 'tiendas': 'Agrega al menos una tienda.'}} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · Revisa los campos marcados. · {'campos': {'dias_programados': 'Selecciona al menos un día de visita.', 'nombre_ruta': 'El nombre de la ruta es obligatorio (máximo 100 caracteres).', 'tiendas': 'Agrega al menos una tienda.'}} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_R06_ruta_sin_dias_ni_tiendas(app, esc, obs):
    """R06 · Ruta sin días ni tiendas
    RF: RF-09; RF-23 mensajes de error
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: nombre vacío, días [], tiendas []
    Esperado: HTTP 400 con mensajes en nombre_ruta, dias_programados y tiendas
    """
    r = obs(cliente(app, "admin@test.mx").post("/api/rutas", json={"id_promotor": esc.ids.p2, "nombre_ruta": "",
                                                                    "dias_programados": [], "tiendas": []}))
    assert r.status_code == 400 and set(r.get_json()["campos"]) == {"nombre_ruta", "dias_programados", "tiendas"}
```

</details>

### U01 · Alta de usuario con datos válidos

- **Requisito / caso de uso:** RF-03 (3.6) Crear/Agregar usuarios
- **Tipo:** válido
- **Precondiciones:** sesión de Administrador; existe el supervisor S1
- **Datos de entrada:** nombre, número de empleado SR-101, teléfono, correo, rol Promotor, supervisor S1
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U01_alta_usuario_valida -v`
- **Resultado esperado:** HTTP 201; cuenta Activa con debe_cambiar_password; sin SMTP se entrega contraseña temporal una vez
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 201 · Usuario registrado correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 201 · Usuario registrado correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U01_alta_usuario_valida(app, esc, obs):
    """U01 · Alta de usuario con datos válidos
    RF: RF-03 (3.6) Crear/Agregar usuarios
    Tipo: válido
    Pre: sesión de Administrador; existe el supervisor S1
    Entrada: nombre, número de empleado SR-101, teléfono, correo, rol Promotor, supervisor S1
    Esperado: HTTP 201; cuenta Activa con debe_cambiar_password; sin SMTP se entrega contraseña temporal una vez
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}))
    assert r.status_code == 201
    d = r.get_json()
    assert d["usuario"]["debe_cambiar_password"] is True and d["usuario"]["estatus"] == "Activo"
    assert d["acceso"]["envio_correo"] == "no_configurado"
    assert len(d["acceso"]["password_temporal"]) == 12
    with app.app_context():
        u = db.session.execute(db.select(Usuario).where(Usuario.correo_electronico == "ana@test.mx")).scalar_one()
        assert u.password_hash.startswith("pbkdf2:") and d["acceso"]["password_temporal"] not in u.password_hash
```

</details>

### U02 · Alta rechazada por campos obligatorios vacíos

- **Requisito / caso de uso:** RF-03 (3.6); RF-23 Mensajes de error
- **Tipo:** inválido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** formulario vacío
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U02_campos_obligatorios -v`
- **Resultado esperado:** HTTP 400 con mensaje por campo (nombre, correo, teléfono, número de empleado, rol)
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · Revisa los campos marcados. · {'campos': {'correo_electronico': 'Escribe un correo electrónico válido.', 'nombre_completo': 'El nombre completo es obligatorio.', 'numero_empleado': 'El número de empleado es obligatorio (letras, números o guiones).', 'rol': 'Selecciona un rol válido.', 'telefono': 'El teléfono es obligatorio (10 a 15 dígitos).'}} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · Revisa los campos marcados. · {'campos': {'correo_electronico': 'Escribe un correo electrónico válido.', 'nombre_completo': 'El nombre completo es obligatorio.', 'numero_empleado': 'El número de empleado es obligatorio (letras, números o guiones).', 'rol': 'Selecciona un rol válido.', 'telefono': 'El teléfono es obligatorio (10 a 15 dígitos).'}} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U02_campos_obligatorios(app, esc, obs):
    """U02 · Alta rechazada por campos obligatorios vacíos
    RF: RF-03 (3.6); RF-23 Mensajes de error
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: formulario vacío
    Esperado: HTTP 400 con mensaje por campo (nombre, correo, teléfono, número de empleado, rol)
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={}))
    assert r.status_code == 400
    assert set(r.get_json()["campos"]) >= {"nombre_completo", "correo_electronico", "telefono", "numero_empleado", "rol"}
```

</details>

### U03 · Correo y número de empleado duplicados

- **Requisito / caso de uso:** RF-03 (3.6) número de empleado único; correo UNIQUE (diccionario)
- **Tipo:** inválido
- **Precondiciones:** existe p1@test.mx con número P1
- **Datos de entrada:** nuevo usuario con correo p1@test.mx y número P1
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U03_duplicados -v`
- **Resultado esperado:** HTTP 400 indicando ambos duplicados; no se crea registro
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · Revisa los campos marcados. · {'campos': {'correo_electronico': 'Ya existe un usuario con ese correo.', 'numero_empleado': 'Ya existe un usuario con ese número de empleado.'}} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · Revisa los campos marcados. · {'campos': {'correo_electronico': 'Ya existe un usuario con ese correo.', 'numero_empleado': 'Ya existe un usuario con ese número de empleado.'}} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U03_duplicados(app, esc, obs):
    """U03 · Correo y número de empleado duplicados
    RF: RF-03 (3.6) número de empleado único; correo UNIQUE (diccionario)
    Tipo: inválido
    Pre: existe p1@test.mx con número P1
    Entrada: nuevo usuario con correo p1@test.mx y número P1
    Esperado: HTTP 400 indicando ambos duplicados; no se crea registro
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json={**NUEVO, "correo_electronico": "P1@test.mx", "numero_empleado": "p1",
                                          "id_supervisor": esc.ids.s1}))
    assert r.status_code == 400
    assert "correo_electronico" in r.get_json()["campos"] and "numero_empleado" in r.get_json()["campos"]
```

</details>

### U04 · Promotor sin supervisor

- **Requisito / caso de uso:** RF-03/RF-07 (3.6) asignar rol y supervisor
- **Tipo:** inválido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** rol Promotor sin id_supervisor
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U04_promotor_requiere_supervisor -v`
- **Resultado esperado:** HTTP 400 en el campo id_supervisor
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 400 · Revisa los campos marcados. · {'campos': {'id_supervisor': 'Asigna un supervisor activo al promotor.'}} → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 400 · Revisa los campos marcados. · {'campos': {'id_supervisor': 'Asigna un supervisor activo al promotor.'}} → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U04_promotor_requiere_supervisor(app, esc, obs):
    """U04 · Promotor sin supervisor
    RF: RF-03/RF-07 (3.6) asignar rol y supervisor
    Tipo: inválido
    Pre: sesión de Administrador
    Entrada: rol Promotor sin id_supervisor
    Esperado: HTTP 400 en el campo id_supervisor
    """
    c = cliente(app, "admin@test.mx")
    r = obs(c.post("/api/usuarios", json=NUEVO))
    assert r.status_code == 400 and "id_supervisor" in r.get_json()["campos"]
```

</details>

### U05 · Supervisor y promotor no pueden registrar usuarios

- **Requisito / caso de uso:** RF-03 (3.6); RNF-16 control de acceso por rol
- **Tipo:** no autorizado
- **Precondiciones:** sesiones de Supervisor S1 y Promotor P1
- **Datos de entrada:** POST /api/usuarios con datos válidos (petición manipulada)
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U05_solo_admin_gestiona -v`
- **Resultado esperado:** HTTP 403 en ambos casos
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 403 · No tienes permiso para esta sección. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 403 · No tienes permiso para esta sección. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U05_solo_admin_gestiona(app, esc, obs):
    """U05 · Supervisor y promotor no pueden registrar usuarios
    RF: RF-03 (3.6); RNF-16 control de acceso por rol
    Tipo: no autorizado
    Pre: sesiones de Supervisor S1 y Promotor P1
    Entrada: POST /api/usuarios con datos válidos (petición manipulada)
    Esperado: HTTP 403 en ambos casos
    """
    for correo in ("s1@test.mx", "p1@test.mx"):
        r = obs(cliente(app, correo).post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}))
        assert r.status_code == 403
```

</details>

### U06 · Consulta y búsqueda de usuarios con alcance por rol

- **Requisito / caso de uso:** RF-04 (3.6) Consultar/Ver listado de usuarios
- **Tipo:** válido / alcance
- **Precondiciones:** S1 supervisa a P1 y P2; S2 supervisa a P3
- **Datos de entrada:** admin busca "P3"; S1 lista sin filtro
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U06_busqueda_y_alcance -v`
- **Resultado esperado:** el admin encuentra a P3 por número de empleado; S1 solo ve a P1 y P2
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U06_busqueda_y_alcance(app, esc, obs):
    """U06 · Consulta y búsqueda de usuarios con alcance por rol
    RF: RF-04 (3.6) Consultar/Ver listado de usuarios
    Tipo: válido / alcance
    Pre: S1 supervisa a P1 y P2; S2 supervisa a P3
    Entrada: admin busca "P3"; S1 lista sin filtro
    Esperado: el admin encuentra a P3 por número de empleado; S1 solo ve a P1 y P2
    """
    r = obs(cliente(app, "admin@test.mx").get("/api/usuarios?q=P3"))
    assert [u["numero_empleado"] for u in r.get_json()["usuarios"]] == ["P3"]
    r = cliente(app, "s1@test.mx").get("/api/usuarios")
    assert sorted(u["numero_empleado"] for u in r.get_json()["usuarios"]) == ["P1", "P2"]
    assert cliente(app, "s1@test.mx").get(f"/api/usuarios/{esc.ids.p3}").status_code == 404
```

</details>

### U07 · Editar datos de un usuario

- **Requisito / caso de uso:** RF-05 (3.6) Editar datos de usuario
- **Tipo:** válido
- **Precondiciones:** sesión de Administrador; P2 pertenece a S1
- **Datos de entrada:** cambiar teléfono y reasignar P2 al supervisor S2
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U07_editar_usuario -v`
- **Resultado esperado:** HTTP 200; el cambio de supervisor modifica el alcance (S2 ve a P2, S1 ya no)
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Datos actualizados correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Datos actualizados correctamente. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U07_editar_usuario(app, esc, obs):
    """U07 · Editar datos de un usuario
    RF: RF-05 (3.6) Editar datos de usuario
    Tipo: válido
    Pre: sesión de Administrador; P2 pertenece a S1
    Entrada: cambiar teléfono y reasignar P2 al supervisor S2
    Esperado: HTTP 200; el cambio de supervisor modifica el alcance (S2 ve a P2, S1 ya no)
    """
    c = cliente(app, "admin@test.mx")
    u = c.get(f"/api/usuarios/{esc.ids.p2}").get_json()["usuario"]
    r = obs(c.put(f"/api/usuarios/{esc.ids.p2}", json={**u, "telefono": "4779998877", "id_supervisor": esc.ids.s2}))
    assert r.status_code == 200 and r.get_json()["usuario"]["telefono"] == "4779998877"
    assert cliente(app, "s2@test.mx").get(f"/api/usuarios/{esc.ids.p2}").status_code == 200
    assert cliente(app, "s1@test.mx").get(f"/api/usuarios/{esc.ids.p2}").status_code == 404
```

</details>

### U08 · Desactivar promotor: baja lógica y liberación de tiendas

- **Requisito / caso de uso:** RF-06 (3.6) Eliminar/Desactivar usuarios
- **Tipo:** válido
- **Precondiciones:** P1 tiene 2 asignaciones hoy sin visita
- **Datos de entrada:** POST /api/usuarios/P1/desactivar
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U08_baja_logica_libera_tiendas -v`
- **Resultado esperado:** estatus Inactivo, registro conservado, asignaciones Canceladas (historial), P1 no puede entrar
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Usuario desactivado. Ya no puede iniciar sesión. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Usuario desactivado. Ya no puede iniciar sesión. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U08_baja_logica_libera_tiendas(app, esc, obs):
    """U08 · Desactivar promotor: baja lógica y liberación de tiendas
    RF: RF-06 (3.6) Eliminar/Desactivar usuarios
    Tipo: válido
    Pre: P1 tiene 2 asignaciones hoy sin visita
    Entrada: POST /api/usuarios/P1/desactivar
    Esperado: estatus Inactivo, registro conservado, asignaciones Canceladas (historial), P1 no puede entrar
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/usuarios/{esc.ids.p1}/desactivar"))
    assert r.status_code == 200 and r.get_json()["asignaciones_liberadas"] == 2
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p1).estatus == "Inactivo"
        estados = db.session.execute(db.select(Asignacion.estado).where(Asignacion.id_promotor == esc.ids.p1)).scalars().all()
        assert estados == ["Cancelada", "Cancelada"]
    r = app.test_client().post("/api/auth/login", json={"correo": "p1@test.mx", "password": "Prueba-1234"})
    assert r.status_code == 403
```

</details>

### U09 · Supervisor con promotores activos no se puede desactivar

- **Requisito / caso de uso:** RF-06 (3.6)
- **Tipo:** inválido (estado incompatible)
- **Precondiciones:** S1 tiene a P1 y P2 activos
- **Datos de entrada:** POST /api/usuarios/S1/desactivar
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U09_no_desactivar_supervisor_con_promotores -v`
- **Resultado esperado:** HTTP 409 pidiendo reasignar a los promotores
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 409 · Este supervisor tiene 2 promotor(es) activos. Reasígnalos a otro supervisor primero. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 409 · Este supervisor tiene 2 promotor(es) activos. Reasígnalos a otro supervisor primero. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U09_no_desactivar_supervisor_con_promotores(app, esc, obs):
    """U09 · Supervisor con promotores activos no se puede desactivar
    RF: RF-06 (3.6)
    Tipo: inválido (estado incompatible)
    Pre: S1 tiene a P1 y P2 activos
    Entrada: POST /api/usuarios/S1/desactivar
    Esperado: HTTP 409 pidiendo reasignar a los promotores
    """
    r = obs(cliente(app, "admin@test.mx").post(f"/api/usuarios/{esc.ids.s1}/desactivar"))
    assert r.status_code == 409
```

</details>

### U10 · La contraseña temporal obliga a cambiarla

- **Requisito / caso de uso:** RF-03 (3.6) entrega de acceso; RNF-16 seguridad
- **Tipo:** válido / restricción
- **Precondiciones:** usuario recién creado con contraseña temporal
- **Datos de entrada:** login con la temporal, consulta su inicio, cambia la contraseña y vuelve a consultar
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U10_contrasena_temporal_obliga_cambio -v`
- **Resultado esperado:** antes del cambio HTTP 403 (codigo cambiar_password); después HTTP 200
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Contraseña actualizada correctamente. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Contraseña actualizada correctamente. → **EXITOSA**
- **Historial:** falló antes de la corrección F02 (ver tabla de fallos).
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U10_contrasena_temporal_obliga_cambio(app, esc, obs):
    """U10 · La contraseña temporal obliga a cambiarla
    RF: RF-03 (3.6) entrega de acceso; RNF-16 seguridad
    Tipo: válido / restricción
    Pre: usuario recién creado con contraseña temporal
    Entrada: login con la temporal, consulta su inicio, cambia la contraseña y vuelve a consultar
    Esperado: antes del cambio HTTP 403 (codigo cambiar_password); después HTTP 200
    """
    admin = cliente(app, "admin@test.mx")
    temporal = admin.post("/api/usuarios", json={**NUEVO, "id_supervisor": esc.ids.s1}).get_json()["acceso"]["password_temporal"]
    c = app.test_client()
    assert c.post("/api/auth/login", json={"correo": "ana@test.mx", "password": temporal}).status_code == 200
    assert c.get("/api/inicio/promotor").get_json()["codigo"] == "cambiar_password"
    r = obs(c.post("/api/auth/cambiar-password", json={"password_actual": temporal, "password_nueva": "NuevaClave2026"}))
    assert r.status_code == 200
    assert c.get("/api/inicio/promotor").status_code == 200
```

</details>

### U11 · Registro de intentos fallidos (política de bloqueo pendiente)

- **Requisito / caso de uso:** RNF-01 inicio de sesión con bloqueo tras 3 intentos (duración PENDIENTE)
- **Tipo:** inválido
- **Precondiciones:** usuario P2 activo
- **Datos de entrada:** 3 contraseñas incorrectas y luego la correcta
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U11_intentos_fallidos_se_registran -v`
- **Resultado esperado:** se cuentan 3 intentos; la cuenta NO se bloquea porque la duración no está definida; el contador vuelve a 0
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 ·  → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 ·  → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U11_intentos_fallidos_se_registran(app, esc, obs):
    """U11 · Registro de intentos fallidos (política de bloqueo pendiente)
    RF: RNF-01 inicio de sesión con bloqueo tras 3 intentos (duración PENDIENTE)
    Tipo: inválido
    Pre: usuario P2 activo
    Entrada: 3 contraseñas incorrectas y luego la correcta
    Esperado: se cuentan 3 intentos; la cuenta NO se bloquea porque la duración no está definida; el contador vuelve a 0
    """
    c = app.test_client()
    for _ in range(3):
        assert c.post("/api/auth/login", json={"correo": "p2@test.mx", "password": "mala"}).status_code == 401
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p2).intentos_fallidos == 3
    r = obs(c.post("/api/auth/login", json={"correo": "p2@test.mx", "password": "Prueba-1234"}))
    assert r.status_code == 200
    with app.app_context():
        assert db.session.get(Usuario, esc.ids.p2).intentos_fallidos == 0
```

</details>

### U12 · Consultar, modificar y restablecer parámetros globales

- **Requisito / caso de uso:** ERS 3.1 portal admin punto 7 (Parámetros globales); diccionario PARÁMETRO
- **Tipo:** válido e inválido
- **Precondiciones:** sesión de Administrador
- **Datos de entrada:** gps_intervalo_min = 5; luego 99 (fuera de rango); luego restablecer
- **Procedimiento:** `cd backend` y `python -m pytest tests/test_usuarios.py::test_U12_parametros_globales -v`
- **Resultado esperado:** 200 con valor 5; 400 por rango 1-10; restablecido a 10; supervisor no puede editar (403)
- **Resultado obtenido · Laptop Windows · SQL Server (base ScribeTracker_Pruebas):** HTTP 200 · Parámetro actualizado. → **EXITOSA**
- **Resultado obtenido · Laptop Windows · SQLite en memoria:** HTTP 200 · Parámetro actualizado. → **EXITOSA**
- **Evidencia:** salida de pytest en `scripts/logs/pruebas.log` y XML JUnit en `docs/pruebas/`.

<details><summary>Código de la prueba</summary>

```python
def test_U12_parametros_globales(app, esc, obs):
    """U12 · Consultar, modificar y restablecer parámetros globales
    RF: ERS 3.1 portal admin punto 7 (Parámetros globales); diccionario PARÁMETRO
    Tipo: válido e inválido
    Pre: sesión de Administrador
    Entrada: gps_intervalo_min = 5; luego 99 (fuera de rango); luego restablecer
    Esperado: 200 con valor 5; 400 por rango 1-10; restablecido a 10; supervisor no puede editar (403)
    """
    c = cliente(app, "admin@test.mx")
    assert len(c.get("/api/parametros").get_json()["parametros"]) >= 10
    r = obs(c.put("/api/parametros/gps_intervalo_min", json={"valor": "5"}))
    assert r.status_code == 200 and r.get_json()["parametro"]["valor_activo"] == "5"
    assert c.put("/api/parametros/gps_intervalo_min", json={"valor": "99"}).status_code == 400
    assert c.post("/api/parametros/gps_intervalo_min/restablecer").get_json()["parametro"]["valor_activo"] == "10"
    assert cliente(app, "s1@test.mx").put("/api/parametros/gps_intervalo_min", json={"valor": "5"}).status_code == 403
```

</details>

