import { HttpClient } from '@angular/common/http';
import { DecimalPipe } from '@angular/common';
import { Component, OnInit, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { duracion, hora, hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { EstadoPromotor, Evidencia, Incidencia, ResumenDia } from '../core/modelos';
import { MapaComponent, MarcadorMapa } from '../shared/mapa.component';
import { SelectorPromotor } from './selector-promotor';

interface DatosSeguimiento extends ResumenDia {
  promotor: { id_usuario: number; nombre_completo: string; numero_empleado: string | null; tipo_contrato: string | null };
  estado: EstadoPromotor | null;
  ubicaciones: { latitud: number; longitud: number; precision_m: number | null; fecha_hora: string; origen: string }[];
  incidencias: Incidencia[];
  rutas: { id_ruta: number; nombre_ruta: string; dias_programados: string }[];
}

/** Seguimiento del día (prototipo "Rutas"), historial de ubicaciones (RF-14) y evidencias. */
@Component({
  selector: 'app-seguimiento',
  imports: [FormsModule, MapaComponent, SelectorPromotor, DecimalPipe],
  template: `
    <section class="tarjeta filtros">
      <label>Promotor <app-selector-promotor [(valor)]="idPromotor" /></label>
      <label>Fecha <input type="date" [(ngModel)]="fecha" (change)="cargar()" /></label>
    </section>
    @if (error()) { <p class="alerta">{{ error() }}</p> }
    @if (d(); as d) {
      <div class="rejilla-mapa">
        <section class="tarjeta">
          <h2>Ruta de: {{ d.promotor.nombre_completo }}</h2>
          <app-mapa [marcadores]="marcadores()" [recorrido]="recorrido()" alto="420px" />
          <p class="nota">Línea azul: {{ d.ubicaciones.length }} ubicaciones registradas ({{ sinConexion() }} enviadas sin conexión). Puntos: check-in (verde), check-out (morado) y fotos fuera de geocerca (rojo).</p>
          @if (!d.jornada) { <p class="nota">No hay registros de jornada para esta fecha.</p> }
        </section>
        <section class="tarjeta">
          <p><b>{{ d.promotor.nombre_completo }}</b> · {{ d.promotor.tipo_contrato || '—' }}</p>
          <p>VISITAS: {{ d.resumen.tiendas_visitadas }}/{{ d.resumen.tiendas_asignadas }} · {{ d.incidencias.length }} incidencia(s)</p>
          @if (d.estado) { <p>Estado actual: {{ d.estado.estado_jornada }} @if (d.estado.estado_visita) { · {{ d.estado.estado_visita }} } · conexión {{ d.estado.estado_conexion }}</p> }
          @if (d.jornada) { <p>🟢 Inicio {{ hora(d.jornada.inicio) }} @if (d.jornada.fin) { · Fin {{ hora(d.jornada.fin) }} } @if (d.jornada.cierre_forzado) { · cierre con pendientes: {{ d.jornada.motivo_cierre }} }</p> }
          @for (a of d.asignaciones; track a.id_asignacion) {
            <p>🏪 {{ a.orden_visita }}. {{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}<br />
              <small>@if (a.visita) { {{ hora(a.visita.checkin) }} – {{ hora(a.visita.checkout) }} · {{ duracion(a.visita.duracion_min) }} · {{ a.visita.estado }} } @else { sin visita }</small></p>
          }
          @if (d.jornada?.pausas?.length) {
            <p>Pausas: @for (p of d.jornada!.pausas; track p.id_pausa) { {{ p.tipo }} {{ hora(p.inicio) }}–{{ hora(p.fin) }} ({{ p.duracion_real_min }}/{{ p.duracion_programada_min }} min); }</p>
          }
          @if (d.rutas.length) { <p class="nota">Rutas activas: @for (r of d.rutas; track r.id_ruta) { {{ r.nombre_ruta }} ({{ r.dias_programados }}) } </p> }
          <h3>Incidencias del día</h3>
          @for (i of d.incidencias; track i.id_incidencia) { <p class="alerta-item">{{ hora(i.fecha_hora) }} · {{ i.tipo }}{{ i.es_critica ? ' (crítica)' : '' }}: {{ i.descripcion }}</p> }
          @empty { <p class="nota">Sin incidencias.</p> }
        </section>
      </div>
      <section class="tarjeta">
        <h2>Evidencias fotográficas</h2>
        @for (a of d.asignaciones; track a.id_asignacion) {
          @if (a.visita?.evidencias?.length) {
            <h3>{{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}</h3>
            <div class="galeria">
              @for (e of a.visita!.evidencias; track e.id_evidencia) {
                <figure [class.mala]="e.estatus_validacion !== 'Válida'">
                  <a [href]="e.url" target="_blank" rel="noopener"><img [src]="e.url" [alt]="e.categoria" loading="lazy" /></a>
                  <figcaption>
                    <b>{{ e.categoria }}</b>{{ e.sin_promocion ? ' (exhibición, sin promoción)' : '' }}<br />
                    {{ hora(e.fecha_hora_captura) }} · {{ e.estatus_validacion }} · {{ e.distancia_m | number: '1.0-0' }} m<br />
                    <small>SHA-256 {{ e.hash_imagen.slice(0, 12) }}… · {{ e.origen }}</small><br />
                    Revisión: {{ e.revision_supervisor }}
                    <span class="fila-botones">
                      <button type="button" class="boton boton--chico" (click)="revisar(e, 'Aprobada')">Aprobar</button>
                      <button type="button" class="boton boton--chico" (click)="revisar(e, 'Observada')">Observar</button>
                    </span>
                  </figcaption>
                </figure>
              }
            </div>
          }
        }
      </section>
    }
  `,
})
export class Seguimiento implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  private readonly ruta = inject(ActivatedRoute);
  readonly idPromotor = signal<number | null>(null);
  fecha = hoyIso();
  readonly d = signal<DatosSeguimiento | null>(null);
  readonly error = signal<string | null>(null);
  readonly hora = hora;
  readonly duracion = duracion;

  constructor() {
    effect(() => { if (this.idPromotor()) void this.cargar(); });
  }

  ngOnInit() {
    const id = Number(this.ruta.snapshot.queryParamMap.get('id_promotor'));
    if (id) this.idPromotor.set(id);
  }

  readonly recorrido = computed<[number, number][]>(() => (this.d()?.ubicaciones ?? []).map((u) => [u.latitud, u.longitud]));
  readonly sinConexion = computed(() => (this.d()?.ubicaciones ?? []).filter((u) => u.origen === 'Sin conexión').length);

  readonly marcadores = computed<MarcadorMapa[]>(() => {
    const d = this.d();
    if (!d) return [];
    const m: MarcadorMapa[] = [];
    for (const a of d.asignaciones) {
      m.push({ lat: a.tienda.latitud, lon: a.tienda.longitud, radio_m: a.tienda.radio_geocerca_m, tipo: 'tienda',
        etiqueta: String(a.orden_visita), color: a.visita?.estado === 'Cerrada' ? '#16a34a' : '#dc2626',
        texto: `${a.orden_visita}. ${a.tienda.nombre_comercial} ${a.tienda.sucursal}` });
      const v = a.visita;
      if (v) {
        m.push({ lat: v.latitud_checkin, lon: v.longitud_checkin, tipo: 'punto', color: '#16a34a', texto: `Check-in ${hora(v.checkin)} (${Math.round(v.distancia_checkin_m)} m)` });
        if (v.latitud_checkout != null && v.longitud_checkout != null) {
          m.push({ lat: v.latitud_checkout, lon: v.longitud_checkout, tipo: 'punto', color: '#7c3aed', texto: `Check-out ${hora(v.checkout)} (${Math.round(v.distancia_checkout_m ?? 0)} m)` });
        }
        v.evidencias.filter((e: Evidencia) => !e.dentro_geocerca).forEach((e) =>
          m.push({ lat: e.latitud, lon: e.longitud, tipo: 'punto', color: '#dc2626', texto: `Foto ${e.categoria} fuera de geocerca (${Math.round(e.distancia_m)} m)` }));
      }
    }
    return m;
  });

  async cargar() {
    if (!this.idPromotor()) return;
    try {
      this.error.set(null);
      this.d.set(await firstValueFrom(this.http.get<DatosSeguimiento>(`/api/supervision/seguimiento?id_promotor=${this.idPromotor()}&fecha=${this.fecha}`)));
    } catch (e) {
      this.error.set(mensajeError(e));
      this.d.set(null);
    }
  }

  async revisar(e: Evidencia, revision: 'Aprobada' | 'Observada') {
    const comentario = revision === 'Observada' ? (prompt('Comentario de la observación:') ?? '') : '';
    try {
      await firstValueFrom(this.http.put(`/api/evidencias/${e.id_evidencia}/revision`, { revision, comentario }));
      this.avisos.ok('Revisión guardada.');
      await this.cargar();
    } catch (err) {
      this.avisos.error(mensajeError(err));
    }
  }
}
