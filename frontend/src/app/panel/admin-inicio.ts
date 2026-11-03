import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { hora, mensajeError } from '../core/api';
import { Incidencia } from '../core/modelos';

interface Resumen {
  usuarios: { total: number; activos: number; promotores: number; supervisores: number };
  tiendas: { total: number; activas: number };
  rutas: { total: number; activas: number };
  parametros: number;
  reportes: number;
  alertas: Incidencia[];
  actividad: { fecha_hora: string; texto: string }[];
}

/** Resumen general del administrador (ERS 3.1, portal admin punto 2). */
@Component({
  selector: 'app-admin-inicio',
  imports: [RouterLink],
  template: `
    <h1 class="bienvenida bienvenida--oscura">¡BIENVENIDO!</h1>
    <div class="mosaico mosaico--panel">
      <a routerLink="../usuarios" class="mosaico__item"><span>👤</span>Usuarios<small>{{ r()?.usuarios?.activos ?? '…' }} activos de {{ r()?.usuarios?.total ?? '…' }}</small></a>
      <a routerLink="../tiendas" class="mosaico__item"><span>🏪</span>Tiendas<small>{{ r()?.tiendas?.activas ?? '…' }} activas de {{ r()?.tiendas?.total ?? '…' }}</small></a>
      <a routerLink="../rutas" class="mosaico__item"><span>🚚</span>Rutas<small>{{ r()?.rutas?.activas ?? '…' }} activas de {{ r()?.rutas?.total ?? '…' }}</small></a>
      <a routerLink="../reportes" class="mosaico__item"><span>📋</span>Reportes<small>{{ r()?.reportes ?? '…' }} generados</small></a>
      <a routerLink="../parametros" class="mosaico__item"><span>⚙</span>Parámetros<small>{{ r()?.parametros ?? '…' }} configurables</small></a>
      <a routerLink="../supervision" class="mosaico__item"><span>🗺</span>Monitoreo<small>mapa en tiempo real</small></a>
    </div>
    @if (error()) { <p class="alerta">{{ error() }}</p> }
    <div class="rejilla-2">
      <section class="tarjeta">
        <h2>🚨 Alertas activas</h2>
        @for (a of r()?.alertas ?? []; track a.id_incidencia) {
          <p class="alerta-item">{{ a.fecha_hora.slice(0, 10) }} {{ hora(a.fecha_hora) }} · <b>{{ a.tipo }}</b> · {{ a.nombre_promotor }}</p>
        } @empty { <p class="nota">Sin alertas críticas pendientes.</p> }
      </section>
      <section class="tarjeta">
        <h2>Últimas actividades</h2>
        @for (x of r()?.actividad ?? []; track $index) { <p>{{ x.fecha_hora.slice(0, 10) }} {{ hora(x.fecha_hora) }} · {{ x.texto }}</p> }
        @empty { <p class="nota">Sin actividad registrada.</p> }
      </section>
    </div>
  `,
})
export class AdminInicio implements OnInit {
  private readonly http = inject(HttpClient);
  readonly r = signal<Resumen | null>(null);
  readonly error = signal<string | null>(null);
  readonly hora = hora;

  async ngOnInit() {
    try {
      this.r.set(await firstValueFrom(this.http.get<Resumen>('/api/admin/resumen')));
    } catch (e) { this.error.set(mensajeError(e)); }
  }
}
