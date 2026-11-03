import { HttpClient } from '@angular/common/http';
import { Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Ruta, Tienda } from '../core/modelos';
import { MapaComponent, MarcadorMapa } from '../shared/mapa.component';
import { BuscadorTiendas } from './buscador-tiendas';
import { SelectorPromotor } from './selector-promotor';

interface AsignacionApi {
  id_asignacion: number; fecha: string; orden_visita: number; estado: string;
  fecha_cancelacion: string | null; motivo_cancelacion: string | null; tienda: Tienda;
  visita: { estado: string } | null;
}

/**
 * Gestión de rutas del supervisor (RF-09): tiendas por fecha y orden de
 * visita. La asignación es manual; quitar una tienda la marca como
 * Cancelada para conservar el historial.
 */
@Component({
  selector: 'app-asignacion',
  imports: [FormsModule, SelectorPromotor, BuscadorTiendas, MapaComponent],
  template: `
    <section class="tarjeta filtros">
      <label>PROMOTOR <app-selector-promotor [(valor)]="idPromotor" /></label>
      <label>FECHA <input type="date" [(ngModel)]="fecha" [min]="hoy" (change)="cargar()" /></label>
    </section>
    @if (idPromotor()) {
      <div class="rejilla-mapa">
        <section class="tarjeta">
          <app-mapa [marcadores]="marcadores()" alto="360px" />
        </section>
        <section class="tarjeta">
          <h2>TIENDAS ASIGNADAS</h2>
          <ol class="lista-orden">
            @for (t of plan(); track t.id_tienda; let i = $index) {
              <li>
                <span>{{ t.nombre_comercial }} {{ t.sucursal }} <small>{{ t.zona || '' }}{{ conVisita().has(t.id_tienda) ? ' · con visita' : '' }}</small></span>
                <span class="fila-botones">
                  <button type="button" class="boton boton--chico" (click)="mover(i, -1)" [disabled]="i === 0">↑</button>
                  <button type="button" class="boton boton--chico" (click)="mover(i, 1)" [disabled]="i === plan().length - 1">↓</button>
                  <button type="button" class="boton boton--chico" (click)="quitar(i)" [disabled]="conVisita().has(t.id_tienda)">✕</button>
                </span>
              </li>
            } @empty { <li class="nota">Sin tiendas para esta fecha.</li> }
          </ol>
          <app-buscador-tiendas (elegida)="agregar($event)" />
          @if (rutas().length) {
            <p>Cargar desde ruta:
              @for (r of rutas(); track r.id_ruta) { <button type="button" class="boton boton--chico" (click)="desdeRuta(r)">{{ r.nombre_ruta }}</button> }
            </p>
          }
          @for (a of avisosRuta(); track a) { <p class="nota">⚠ {{ a }}</p> }
          <button type="button" class="boton boton--rojo boton--grande" (click)="guardar()" [disabled]="guardando()">GUARDAR RUTA</button>
          <label class="check"><input type="checkbox" [(ngModel)]="verHistorial" (change)="cargar()" /> Ver historial (incluye canceladas)</label>
          @if (verHistorial) {
            <table class="tabla tabla--chica">
              <tr><th>Tienda</th><th>Orden</th><th>Estado</th><th>Motivo</th></tr>
              @for (a of historial(); track a.id_asignacion) {
                <tr><td>{{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}</td><td>{{ a.orden_visita }}</td><td>{{ a.estado }}</td><td>{{ a.motivo_cancelacion || '' }}</td></tr>
              }
            </table>
          }
        </section>
      </div>
    }
  `,
})
export class Asignacion {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly hoy = hoyIso();
  readonly idPromotor = signal<number | null>(null);
  fecha = hoyIso();
  verHistorial = false;
  readonly plan = signal<Tienda[]>([]);
  readonly historial = signal<AsignacionApi[]>([]);
  readonly conVisita = signal<Set<number>>(new Set());
  readonly rutas = signal<Ruta[]>([]);
  readonly avisosRuta = signal<string[]>([]);
  readonly guardando = signal(false);

  readonly marcadores = computed<MarcadorMapa[]>(() => this.plan().map((t, i) => ({
    lat: t.latitud, lon: t.longitud, radio_m: t.radio_geocerca_m, tipo: 'tienda', etiqueta: String(i + 1),
    color: '#E30613', texto: `${i + 1}. ${t.nombre_comercial} ${t.sucursal}`,
  })));

  constructor() {
    effect(() => { if (this.idPromotor()) void this.cargar(); });
  }

  async cargar() {
    const id = this.idPromotor();
    if (!id) return;
    try {
      const r = await firstValueFrom(this.http.get<{ asignaciones: AsignacionApi[] }>(
        `/api/asignaciones?id_promotor=${id}&fecha=${this.fecha}&historial=1`));
      const activas = r.asignaciones.filter((a) => a.estado === 'Activa').sort((a, b) => a.orden_visita - b.orden_visita);
      this.plan.set(activas.map((a) => a.tienda));
      this.conVisita.set(new Set(activas.filter((a) => a.visita).map((a) => a.tienda.id_tienda)));
      this.historial.set(r.asignaciones);
      this.rutas.set((await firstValueFrom(this.http.get<{ rutas: Ruta[] }>(`/api/rutas?id_promotor=${id}&estado=Activa`))).rutas);
      this.avisosRuta.set([]);
    } catch (e) {
      this.avisos.error(mensajeError(e));
    }
  }

  agregar(t: Tienda) {
    if (this.plan().some((x) => x.id_tienda === t.id_tienda)) {
      this.avisos.alerta('Esa tienda ya está en la lista.');
      return;
    }
    this.plan.update((p) => [...p, t]);
  }

  quitar(i: number) { this.plan.update((p) => p.filter((_, j) => j !== i)); }

  mover(i: number, d: number) {
    this.plan.update((p) => {
      const c = [...p];
      [c[i], c[i + d]] = [c[i + d], c[i]];
      return c;
    });
  }

  desdeRuta(r: Ruta) {
    this.plan.set(r.tiendas.map((t) => t as Tienda));
    this.avisos.info(`Se cargaron las tiendas de "${r.nombre_ruta}". Revisa y guarda.`);
  }

  async guardar() {
    this.guardando.set(true);
    try {
      const r = await firstValueFrom(this.http.put<{ mensaje: string; advertencias: string[] }>('/api/asignaciones/dia', {
        id_promotor: this.idPromotor(), fecha: this.fecha, tiendas: this.plan().map((t) => t.id_tienda),
      }));
      this.avisos.ok(r.mensaje);
      await this.cargar();
      this.avisosRuta.set(r.advertencias);
    } catch (e) {
      this.avisos.error(mensajeError(e));
    } finally {
      this.guardando.set(false);
    }
  }
}
