import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { hora } from '../core/api';
import { RastreoService } from '../core/rastreo.service';
import { PromotorService } from './promotor.service';

type Vista = 'menu' | 'perfil' | 'notificaciones' | 'ayuda' | 'sincronizacion';

@Component({
  selector: 'app-configuracion-promotor',
  imports: [RouterLink],
  template: `
    @switch (vista()) {
      @case ('menu') {
        <div class="menu-blanco">
          <button type="button" (click)="abrir('perfil')">MI PERFIL 👤</button>
          <button type="button" (click)="abrir('notificaciones')">NOTIFICACIONES 🔔</button>
          <button type="button" (click)="vista.set('sincronizacion')">SINCRONIZACIÓN ⇅ ({{ ps.cola.pendientes().length }})</button>
          <button type="button" (click)="vista.set('ayuda')">AYUDA ⁉</button>
          <a routerLink="/cambiar-password">CAMBIAR CONTRASEÑA 🔑</a>
        </div>
        <button type="button" class="boton boton--rojo boton--grande" (click)="salir()">CERRAR SESIÓN</button>
      }
      @case ('perfil') {
        @let u = auth.usuario();
        <div class="perfil">
          <div class="avatar">👤</div>
          <label>NOMBRE COMPLETO:</label><p class="caja-blanca">{{ u?.nombre_completo }}</p>
          <label>ID:</label><p class="caja-blanca">{{ u?.numero_empleado || 'Sin número' }}</p>
          <label>ACTIVO DESDE:</label><p class="caja-blanca">{{ u?.fecha_alta?.slice(0, 10) || '—' }}</p>
          <label>TEMPORADA / PLANTA:</label><p class="caja-blanca">{{ u?.tipo_contrato || '—' }}</p>
          <label>SUPERVISOR:</label><p class="caja-blanca">{{ u?.nombre_supervisor || '—' }}</p>
          <label>TIENDAS ASIGNADAS:</label>
          <ul class="caja-blanca">@for (t of tiendas(); track t) { <li>{{ t }}</li> } @empty { <li>—</li> }</ul>
        </div>
        <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
      }
      @case ('notificaciones') {
        @for (n of notificaciones(); track $index) {
          <div class="caja-blanca"><b>{{ n.grupo }}:</b> {{ n.texto }}<br /><small>🕒 {{ n.fecha_hora.slice(0, 10) }} {{ hora(n.fecha_hora) }}</small></div>
        } @empty { <p class="nota">Sin notificaciones en los últimos 7 días.</p> }
        <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
      }
      @case ('sincronizacion') {
        <p class="estado-linea">Conexión: {{ ps.cola.enLinea() ? 'En línea' : 'Sin conexión' }}</p>
        <p class="nota">Seguimiento: {{ rastreo.activo() ? 'activo' : 'detenido' }} · último envío {{ hora(rastreo.ultimoEnvio()) }}
          @if (rastreo.ultimoError()) { · {{ rastreo.ultimoError() }} }</p>
        <h2 class="subtitulo">Pendientes de sincronizar ({{ ps.cola.pendientes().length }})</h2>
        @for (e of ps.cola.pendientes(); track e.id) {
          <div class="caja-blanca">⏳ {{ e.descripcion }} · capturado {{ hora(e.capturado_en) }} · intentos {{ e.intentos }}</div>
        } @empty { <p class="nota">Todo está sincronizado con el servidor.</p> }
        @if (ps.cola.rechazados().length) {
          <h2 class="subtitulo">Rechazados por el servidor</h2>
          @for (e of ps.cola.rechazados(); track e.id) {
            <div class="caja-blanca rechazo">✖ {{ e.descripcion }} ({{ hora(e.capturado_en) }}): {{ e.mensaje }}
              <button type="button" class="boton boton--chico" (click)="ps.cola.descartar(e.id)">Descartar</button></div>
          }
        }
        <button type="button" class="boton boton--rojo" (click)="sincronizar()" [disabled]="ps.cola.sincronizando()">SINCRONIZAR AHORA</button>
        <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
      }
      @case ('ayuda') {
        <div class="caja-blanca">¿Cómo inicio mi jornada? Ve a Entrada/salida y presiona INICIAR JORNADA estando en tu primera tienda.</div>
        <div class="caja-blanca">¿Cómo registro mi llegada? Presiona CHECK-IN en la tienda de la lista cuando estés dentro de ella.</div>
        <div class="caja-blanca">¿Cómo tomo una foto? En la visita, elige la categoría, presiona CAPTURAR y luego ENVIAR. Necesitas Anaquel antes, Anaquel después, Precios y Promociones.</div>
        <div class="caja-blanca">¿Cómo activo una pausa? Ve a Pausas y selecciona Comida o Descanso.</div>
        <div class="caja-blanca">CONTÁCTANOS: +52 (55) 9126-6001 · contacto&#64;biopappel.com</div>
        <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
      }
    }
  `,
})
export class ConfiguracionPromotor {
  readonly auth = inject(AuthService);
  readonly ps = inject(PromotorService);
  readonly rastreo = inject(RastreoService);
  private readonly http = inject(HttpClient);
  readonly vista = signal<Vista>('menu');
  readonly tiendas = signal<string[]>([]);
  readonly notificaciones = signal<{ grupo: string; texto: string; fecha_hora: string }[]>([]);
  readonly hora = hora;

  async abrir(v: Vista) {
    this.vista.set(v);
    try {
      if (v === 'perfil') {
        this.tiendas.set((await firstValueFrom(this.http.get<{ tiendas_autorizadas: string[] }>('/api/promotor/perfil'))).tiendas_autorizadas);
      } else if (v === 'notificaciones') {
        this.notificaciones.set((await firstValueFrom(this.http.get<{ notificaciones: any[] }>('/api/promotor/notificaciones'))).notificaciones);
      }
    } catch { /* sin conexión: se muestra lo disponible */ }
  }

  async sincronizar() {
    await this.ps.cola.sincronizar();
    await this.ps.cargar();
  }

  async salir() {
    const n = this.ps.cola.pendientes().length;
    if (n && !confirm(`Tienes ${n} registro(s) sin sincronizar. ¿Cerrar sesión de todos modos?`)) return;
    await this.auth.cerrarSesion();
  }
}
