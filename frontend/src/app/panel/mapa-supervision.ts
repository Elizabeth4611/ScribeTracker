import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { hora, mensajeError } from '../core/api';
import { EstadoPromotor, Incidencia, Tienda } from '../core/modelos';
import { MapaComponent, MarcadorMapa } from '../shared/mapa.component';
import { colorEstado, textoEstado } from './colores';

interface FilaMapa extends EstadoPromotor {
  id_usuario: number;
  nombre_completo: string;
  numero_empleado: string | null;
  tiendas: (Tienda & { orden_visita: number; visita_estado: string | null })[];
  visitadas: number;
  asignadas: number;
  pausas_hoy: number;
}

interface RespuestaMapa {
  fecha: string;
  hora_servidor: string;
  promotores: FilaMapa[];
  resumen: Record<string, number>;
  alertas: Incidencia[];
  ubicacion_reciente_min: number;
}

/** Mapa en tiempo real (RF-10) con estados separados y alertas críticas (RF-11). */
@Component({
  selector: 'app-mapa-supervision',
  imports: [MapaComponent, RouterLink],
  template: `
    @if (error()) { <p class="alerta">{{ error() }}</p> }
    @let d = datos();
    <div class="rejilla-mapa">
      <section class="tarjeta">
        <app-mapa [marcadores]="marcadores()" alto="440px" />
        <p class="leyenda">
          <span><i style="background:#16a34a"></i>En tienda</span><span><i style="background:#eab308"></i>En traslado</span>
          <span><i style="background:#dc2626"></i>En pausa</span><span><i style="background:#111827"></i>Desconectado</span>
          <span><i style="background:#9ca3af"></i>Sin jornada / finalizada</span>
          <span>Tiendas: borde verde visitada, rojo pendiente</span>
        </p>
        <p class="nota">Actualizado {{ hora(d?.hora_servidor) }} · se refresca cada minuto. Ubicación "desactualizada": más de {{ d?.ubicacion_reciente_min }} min sin datos.</p>
      </section>
      <section class="tarjeta">
        <h2>RESUMEN</h2>
        <ul class="resumen-estados">
          <li>🟢 En tienda: {{ d?.resumen?.['En tienda'] ?? 0 }}</li>
          <li>🟡 En traslado: {{ d?.resumen?.['En traslado'] ?? 0 }}</li>
          <li>🔴 En pausa: {{ d?.resumen?.['En pausa'] ?? 0 }}</li>
          <li>⚫ Desconectados: {{ d?.resumen?.['Desconectados'] ?? 0 }}</li>
          <li>⚪ Sin jornada: {{ d?.resumen?.['Sin jornada'] ?? 0 }} · Finalizada: {{ d?.resumen?.['Finalizada'] ?? 0 }}</li>
        </ul>
        <h2>🚨 ALERTAS CRÍTICAS</h2>
        @for (a of d?.alertas ?? []; track a.id_incidencia) {
          <div class="alerta-item"><b>{{ a.tipo }}</b> · {{ a.nombre_promotor }} · {{ hora(a.fecha_hora) }}<br /><small>{{ a.descripcion }}</small></div>
        } @empty { <p class="nota">Sin alertas críticas pendientes.</p> }
        <a routerLink="../incidencias" class="enlace">Ver incidencias →</a>
      </section>
    </div>
    <section class="tarjeta">
      <h2>Promotores</h2>
      <table class="tabla">
        <thead><tr><th>Promotor</th><th>Cuenta</th><th>Jornada</th><th>Visita</th><th>Conexión</th><th>Última ubicación</th><th>Visitas</th><th>Pausas</th><th></th></tr></thead>
        <tbody>
          @for (p of d?.promotores ?? []; track p.id_usuario) {
            <tr>
              <td><span class="punto" [style.background]="color(p)"></span> {{ p.nombre_completo }} <small>{{ p.numero_empleado }}</small></td>
              <td>{{ p.estado_cuenta }}</td><td>{{ p.estado_jornada }}</td>
              <td>{{ p.estado_visita ?? '—' }} @if (p.tienda_actual) { <small>{{ p.tienda_actual }}</small> }</td>
              <td>{{ p.estado_conexion }}</td><td>{{ hora(p.ultima_ubicacion?.fecha_hora) }}</td>
              <td>{{ p.visitadas }}/{{ p.asignadas }}</td><td>{{ p.pausas_hoy }}</td>
              <td><a [routerLink]="['../seguimiento']" [queryParams]="{ id_promotor: p.id_usuario }" class="enlace">Ver ruta</a></td>
            </tr>
          } @empty { <tr><td colspan="9">No hay promotores activos a tu cargo.</td></tr> }
        </tbody>
      </table>
    </section>
  `,
})
export class MapaSupervision implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  readonly datos = signal<RespuestaMapa | null>(null);
  readonly error = signal<string | null>(null);
  readonly hora = hora;
  readonly color = colorEstado;
  private t?: ReturnType<typeof setInterval>;

  readonly marcadores = computed<MarcadorMapa[]>(() => {
    const d = this.datos();
    if (!d) return [];
    const m: MarcadorMapa[] = [];
    const vistas = new Set<number>();
    for (const p of d.promotores) {
      for (const t of p.tiendas) {
        if (vistas.has(t.id_tienda)) continue;
        vistas.add(t.id_tienda);
        m.push({ lat: t.latitud, lon: t.longitud, radio_m: t.radio_geocerca_m, tipo: 'tienda', etiqueta: '🏪',
          color: t.visita_estado === 'Cerrada' ? '#16a34a' : '#dc2626',
          texto: `${t.nombre_comercial} ${t.sucursal}<br>${p.nombre_completo}: ${t.visita_estado ?? 'sin visitar'}` });
      }
      if (p.ultima_ubicacion) {
        m.push({ lat: p.ultima_ubicacion.latitud, lon: p.ultima_ubicacion.longitud, tipo: 'persona', color: colorEstado(p),
          etiqueta: p.nombre_completo.split(' ').map((x) => x[0]).join('').slice(0, 2),
          texto: `<b>${p.nombre_completo}</b><br>${textoEstado(p)}<br>Última ubicación: ${p.ultima_ubicacion.fecha_hora.replace('T', ' ').slice(0, 16)} (${p.estado_conexion})` });
      }
    }
    return m;
  });

  ngOnInit() {
    void this.cargar();
    this.t = setInterval(() => void this.cargar(), 60_000);
  }

  ngOnDestroy() { clearInterval(this.t); }

  async cargar() {
    try {
      this.datos.set(await firstValueFrom(this.http.get<RespuestaMapa>('/api/supervision/mapa')));
      this.error.set(null);
    } catch (e) {
      this.error.set(mensajeError(e));
    }
  }
}
