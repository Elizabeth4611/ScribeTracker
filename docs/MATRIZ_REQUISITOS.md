# Matriz de requisitos · ScribeTracker

Fuentes: **ERS** = *ERS con IEEE830* (secciones 3.5 y 3.6, diccionario de datos del Apéndice 3, entrevista del Apéndice 4); **MD** = *Modelo de diseño 2* (casos de uso); **PP** = prototipo *Interfaz de usuario – Promotor* (incluye supervisor); **PA** = prototipo *Portal web – Administrador*; **C1–C9 / D** = reglas confirmadas en el mensaje del 2 de noviembre.

Los números RF se repiten entre secciones del ERS (3.5 y 3.6) y la tabla de priorización los llama RNF. Por eso cada requisito se identifica por **código + sección + nombre**.

Estados: **Probado** = implementado y con pruebas automáticas o E2E que pasan · **Implementado** = funciona sin prueba automática específica · **Parcial** = implementado con un límite documentado · **Pendiente**.

## Acceso y usuarios

| Requisito (fuente) | Función | Estado | Pruebas | Limitaciones / decisiones pendientes |
|---|---|---|---|---|
| RF-01 (3.6) Inicio de sesión (ERS, MD) | Login con correo y contraseña; valida contraseña (hash) y estatus Activo | Probado | AUT01-AUT10, U10, U11 | Los prototipos piden **ID de empleado**; el ERS y el MD piden **correo**. Se usa correo (**pendiente de confirmar**). |
| RNF-01 Bloqueo tras 3 intentos (ERS priorización) | Se cuentan los intentos fallidos (`Intentos_Fallidos`) | Parcial | U11 | **Duración del bloqueo sin definir**: no se bloquea la cuenta. |
| RF-02 (3.6) Cerrar sesión | Cierre de sesión que invalida la cookie | Probado | AUT logout | — |
| RF-03 (3.6) Crear usuarios | Alta con nombre, número de empleado único, rol, teléfono, correo y supervisor | Probado | U01-U05 | El diccionario no traía número de empleado y permitía teléfono nulo; se siguió al ERS (ambos obligatorios en altas y ediciones; las columnas aceptan NULL para los registros anteriores). |
| RF-03 (3.6) Envío de credenciales por correo | Contraseña temporal + cambio obligatorio; envío por SMTP si se configura | Parcial | U01, U10 | Sin SMTP en `.env`, la contraseña temporal se muestra **una sola vez** al administrador. El alta y el envío son pasos separados (no hay duplicados si falla el correo). |
| PP/PA "¿Olvidaste tu contraseña?" | Pantalla de recuperación | Parcial | — | Requiere SMTP; por ahora indica pedir una contraseña temporal al administrador. |
| RF-04 (3.6) Consultar/buscar usuarios | Lista paginada, búsqueda por nombre/número/correo, filtros de rol y estatus | Probado | U06 | El supervisor solo ve a sus promotores. |
| RF-05 (3.6) Editar usuario | Edición con validación; reasignar supervisor | Probado | U07 | No se puede cambiar el propio rol. |
| RF-06 (3.6) Baja lógica | Estatus Inactivo, fecha de baja; libera asignaciones futuras sin visita y desactiva sus rutas | Probado | U08, U09 | Un supervisor con promotores activos no se puede dar de baja hasta reasignarlos. |
| RF-07 (3.6) Roles y permisos | Promotor, Supervisor, Administrador validados en el servidor | Probado | AUT matriz, U05, A01, R03, I03, REP02 | El ERS menciona **Gerente de Zona**: no está en el diccionario ni en el modelo; **pendiente de definir**. |
| ERS 3.1 punto 7 Parámetros globales | Consultar, editar y restablecer (geocerca, GPS, pausas, tolerancias) | Probado | U12 | — |

## Tiendas y rutas

| Requisito (fuente) | Función | Estado | Pruebas | Limitaciones / decisiones pendientes |
|---|---|---|---|---|
| RF-19 Agregar tiendas (ERS, MD, PA) | Alta con nombre, cadena, sucursal, dirección, zona, coordenadas, radio y tiempo estimado; selección en mapa | Probado | T01, T02, T06 | Mapa con OpenStreetMap (Google Maps requiere clave y facturación). |
| RF-20 Listado y filtros | Búsqueda y filtros por cadena, zona y estado | Probado | T03 | — |
| RF-21 Desactivar tiendas | Baja lógica; bloqueada si está en una ruta activa o tiene visitas programadas | Probado | T04, T05 | — |
| Edición de tiendas (PA, MD) | Editar datos y geocerca | Implementado | — | Cambiar coordenadas solo afecta validaciones futuras. |
| RF-09 Asignación y gestión de rutas (ERS, MD, PP) | Asignación manual por fecha y orden; historial con estado Cancelada; plantillas de ruta con días y aplicación a rangos | Probado | R01-R06 | **Cantidad diaria**: RF-09 dice 3 a 4 tiendas, pero la entrevista (P10-P11) menciona tiendas de 5 horas. Se **advierte** si sale de 3-4, sin bloquear. La validación de "misma zona" también es una advertencia. Sin optimización automática (Limitación 6). |

## Jornadas, visitas y evidencias

| Requisito (fuente) | Función | Estado | Pruebas | Limitaciones / decisiones pendientes |
|---|---|---|---|---|
| RF-01 (3.5) Inicio de jornada; C1, C2 | Una jornada por fecha; solo dentro de la geocerca de la primera tienda asignada | Probado | J01-J04, E2E-01, E2E-02 | — |
| C3, RF-03 Check-in; C4 | Separado del inicio; valida geocerca y guarda fecha, hora y coordenadas propias | Probado | V01, V02, E2E-03 | — |
| C9 Duplicados y estados incompatibles | Sin dos visitas abiertas, sin repetir tienda, sin acciones en pausa (índices filtrados + reglas) | Probado | V03, P03, O01 | — |
| RF-04 Check-out; C5, C6, C7 | Nueva ubicación validada; cierra la visita y deja la jornada abierta | Probado | V05, V06, E2E-05 | — |
| C8 Fin de jornada | Separado; exige check-out y fin de pausa; con tiendas pendientes pide motivo y genera incidencia | Probado | J06, J07 | El cierre forzado con motivo es una **decisión propuesta** (tienda cerrada, etc.): falta aprobación. |
| RF-05 Fotos sin galería | Cámara integrada (getUserMedia + lienzo); sin selector de archivos | Parcial | E2E-04 | Un navegador no puede garantizar que la cámara no sea virtual. |
| RF-06 Clasificación; regla D | 4 categorías obligatorias; Promociones admite foto de exhibición Scribe | Probado | E01, V04, V05, E2E-04 | El MD lista también "Entrada/Salida" como categorías; se siguieron las 4 de RF-06 y la regla D. |
| RNF-13 / RF-12 Metadatos y validación | Hash SHA-256, fecha y hora de captura y recepción, coordenadas, distancia y resultado guardados; fuera de geocerca o repetida no cuenta | Probado | E01-E04, E2E-04 | **No detecta imágenes generadas por IA** (ver límites). |
| Separación Visita / Evidencia | Tablas `Visita` y `Evidencia`; varias fotos por visita | Probado | E01-E03 | El diccionario tenía foto y visita en una sola tabla. |
| RF-07 Historial del promotor | Por fecha: tiendas, horarios, horas en tienda, pausas y fotos | Probado | J07 | — |
| RF-08 Pausas | 1 comida (60 min) y 2 descansos (20 min) con temporizador; una a la vez; excedida → incidencia | Probado | P01, P02, E2E-06 | — |

## Seguimiento, incidencias y reportes

| Requisito (fuente) | Función | Estado | Pruebas | Limitaciones / decisiones pendientes |
|---|---|---|---|---|
| RF-02 Ubicación en tiempo real; RNF-15 | Envío cada `gps_intervalo_min` (10) durante la jornada; se detiene en pausa y al cerrar (cliente y servidor) | Parcial | P02, O04, E2E-06 | Una página web **no rastrea con el navegador cerrado o en segundo plano**. |
| RF-10 Mapa en tiempo real | Última ubicación con fecha y hora; reciente o desactualizada; estados de cuenta, jornada, visita y conexión | Probado | S01, S02, E2E-08 | Se actualiza cada 60 s (sin WebSockets). |
| RF-14 Historial de ubicaciones | Recorrido del día en el mapa, check-in/out y fotos fuera de geocerca | Probado | S03 | — |
| RF-11 Alertas automáticas | Críticas: sin llegada a la primera tienda, inactividad fuera de tienda, sin ubicación reciente, fotos sospechosas | Probado | I01, I02, E01-E03 | **Canal: notificación interna en el panel**. El ERS y el MD piden WhatsApp o push: **no integrados**. **Tolerancia**: 20 min (entrevista P16, retardo) y 30 min (RF-11, alerta) quedan como parámetros separados hasta confirmar. 2 h inmóvil **dentro** de una visita no alerta (tiendas de 5 h). |
| RF-18 Historial de incidencias; OBJ-05 seguimiento | Consulta con filtros; estados Pendiente/Revisada/Sancionada con comentario; alta manual | Probado | I03 | La revisión manual de evidencias (Aprobar/Observar) es informativa y no reabre visitas. |
| RF-13 Reportes diarios, semanales y mensuales | Desempeño, Incidencias y Exhibición con datos reales y alcance por rol | Probado | REP01, REP03, E2E-09 | — |
| RF-15 / RF-17 Desempeño individual | Visitadas vs asignadas, tiempo promedio, puntualidad, salidas anticipadas, pausas, fotos e incidencias | Probado | REP01 | "Solicitudes de ajuste aprobadas y rechazadas" **no está especificado** en ninguna fuente. |
| RF-16 Exportar PDF | PDF con tablas y fotos de exhibición | Probado | REP02, REP04, E2E-09 | **Excel**: aparece en la priorización y en los prototipos, pero no en RF-16; queda **pendiente de confirmar**. |
| RF-22 / RF-23 Mensajes | Confirmaciones y errores claros en cada acción | Implementado | E2E-01…09 | — |

## Sin conexión

| Requisito (fuente) | Función | Estado | Pruebas | Limitaciones / decisiones pendientes |
|---|---|---|---|---|
| RNF-08 / RNF-09 Funcionamiento y almacenamiento sin conexión | Cola en IndexedDB con ID de cliente, hora de captura y orden; reintentos idempotentes; el servidor valida cada evento al recibirlo; estados "pendiente" y "confirmado" separados | Probado | O01-O04, E2E-07 (F07 corregido), CP-28 (F08 corregido) | Contradicción: la sección 2.6 lo deja "para más adelante" y RNF-08 le da prioridad alta; se implementó. Se confía en el reloj del dispositivo para la hora de captura (se rechazan horas futuras). |

## Límites técnicos (requieren capacidades adicionales)

| Tema | Situación con Angular + Flask | Alternativa concreta |
|---|---|---|
| Seguimiento con el navegador cerrado o en segundo plano | El sistema operativo suspende la página; el rastreo solo funciona con la app abierta | Empaquetar con **Capacitor** y un complemento de geolocalización en segundo plano, o una app Android nativa |
| Detección de GPS simulado | El navegador no expone si hay ubicaciones simuladas | API de Android (`isMock` / `isFromMockProvider`) en app nativa; por ahora: heurística de velocidad imposible (> 200 km/h → incidencia "Ubicación sospechosa") |
| Detección de imágenes generadas por IA | Cámara en vivo, hash y metadatos **no equivalen** a detectar IA | Servicio de detección o firma de contenido (C2PA) en el dispositivo; revisión del supervisor |
| Autenticidad de coordenadas | La geocerca valida las coordenadas recibidas, no prueba que sean reales | Atestación del dispositivo (Play Integrity) en app nativa |
| Cámara y GPS en el teléfono | Requieren contexto seguro: `http://localhost` o HTTPS | Para probar en el celular: servir con HTTPS (`ng serve --ssl` y certificado de confianza) |
| Alertas por WhatsApp / push | Solo notificación interna | WhatsApp Business Platform (cuenta de Meta, número verificado y plantillas aprobadas) o Web Push (HTTPS, service worker y claves VAPID) |

## Contradicciones registradas

1. El **diagrama E-R** del modelo de diseño contiene entidades de otro proyecto (`PERSONA_REGISTRADA`, `id_condominio`, `numero_casa`, `id_vivienda`). Se tomó el diccionario de datos del ERS como base.
2. **Login por ID** (prototipos) frente a **correo** (ERS 3.1, MD RF-01).
3. **Tolerancia de 20 min** (entrevista P16) frente a **30 min** (RF-11).
4. **3-4 tiendas diarias** (RF-09, P9) frente a **tiendas de 5 h** (P10-P11).
5. **Sin conexión**: ERS 2.6 ("más adelante") frente a RNF-08 (prioridad alta).
6. **Categorías de foto**: RF-06 y la regla D (4 categorías) frente a ERS 2.1/MD (Entrada, Salida, Anaquel, Promos).
7. **Tecnología**: el ERS menciona Android nativo, Flutter, React, MySQL, PostGIS y Google Maps; se mantienen Angular, Flask y SQL Server (con OpenStreetMap).
8. **Gerente de Zona** aparece en RF-07 (3.6), pero no en el diccionario.
