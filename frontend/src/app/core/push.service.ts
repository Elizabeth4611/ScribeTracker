import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

/** Notificaciones push del supervisor (RF-11, etapa 3). Requieren HTTPS o localhost. */
@Injectable({ providedIn: 'root' })
export class PushService {
  private readonly http = inject(HttpClient);
  readonly estado = signal<'no-soportado' | 'bloqueado' | 'inactivo' | 'activo'>('inactivo');

  get soportado(): boolean {
    return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window && window.isSecureContext;
  }

  async revisar(): Promise<void> {
    if (!this.soportado) { this.estado.set('no-soportado'); return; }
    if (Notification.permission === 'denied') { this.estado.set('bloqueado'); return; }
    const reg = await navigator.serviceWorker.getRegistration('/');
    const sub = await reg?.pushManager.getSubscription();
    this.estado.set(sub ? 'activo' : 'inactivo');
  }

  async activar(): Promise<string> {
    if (!this.soportado) throw new Error('Este navegador no permite notificaciones push (se necesita HTTPS o localhost).');
    const permiso = await Notification.requestPermission();
    if (permiso !== 'granted') { this.estado.set('bloqueado'); throw new Error('No diste permiso para mostrar notificaciones.'); }
    const reg = await navigator.serviceWorker.register('/sw-push.js', { scope: '/' });
    await navigator.serviceWorker.ready;
    const { clave_publica } = await firstValueFrom(this.http.get<{ clave_publica: string }>('/api/push/clave'));
    // Si el servicio de push del navegador no responde (sin internet o bloqueado), no se queda esperando.
    const sub = await Promise.race([
      reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: base64UrlABytes(clave_publica) }).catch((e: unknown) => {
        throw new Error((e as { name?: string })?.name === 'NotAllowedError'
          ? 'El navegador no permitió activar las notificaciones push. Revisa los permisos del sitio e inténtalo de nuevo.'
          : 'No se pudo activar el servicio de notificaciones del navegador. Inténtalo de nuevo.');
      }),
      new Promise<never>((_, rechazar) => setTimeout(() => rechazar(new Error(
        'El servicio de notificaciones del navegador no respondió. Revisa tu conexión a internet e inténtalo de nuevo.')), 15000)),
    ]);
    const r = await firstValueFrom(this.http.post<{ mensaje: string }>('/api/push/suscribir', sub.toJSON()));
    this.estado.set('activo');
    return r.mensaje;
  }

  async desactivar(): Promise<string> {
    const reg = await navigator.serviceWorker.getRegistration('/');
    const sub = await reg?.pushManager.getSubscription();
    if (sub) {
      await firstValueFrom(this.http.post('/api/push/cancelar', { endpoint: sub.endpoint }));
      await sub.unsubscribe();
    }
    this.estado.set('inactivo');
    return 'Notificaciones desactivadas en este navegador.';
  }

  async probar(): Promise<string> {
    return (await firstValueFrom(this.http.post<{ mensaje: string }>('/api/push/probar', {}))).mensaje;
  }
}

function base64UrlABytes(texto: string): Uint8Array<ArrayBuffer> {
  const relleno = '='.repeat((4 - (texto.length % 4)) % 4);
  const bin = atob((texto + relleno).replace(/-/g, '+').replace(/_/g, '/'));
  const bytes = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
