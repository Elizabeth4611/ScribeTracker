/* Service worker de notificaciones push (RF-11, etapa 3).
   Muestra las alertas críticas que envía el servidor y, al tocarlas, abre el panel. */
self.addEventListener('push', (evento) => {
  let datos = {};
  try { datos = evento.data ? evento.data.json() : {}; } catch { datos = { cuerpo: evento.data?.text() }; }
  evento.waitUntil(self.registration.showNotification(datos.titulo || 'ScribeTracker', {
    body: datos.cuerpo || '',
    data: { url: datos.url || '/panel/incidencias' },
    tag: 'scribetracker-alerta',
    renotify: true,
  }));
});

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const url = evento.notification.data?.url || '/panel/incidencias';
  evento.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((ventanas) => {
    for (const v of ventanas) {
      if ('focus' in v) { v.navigate(url); return v.focus(); }
    }
    return self.clients.openWindow(url);
  }));
});
