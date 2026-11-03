import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { hora, hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Incidencia } from '../core/modelos';
import { SelectorPromotor } from './selector-promotor';

/** Historial de incidencias (RF-18) y seguimiento manual (OBJ-05). */
@Component({
  selector: 'app-incidencias',
  imports: [FormsModule, SelectorPromotor],
  template: `
    <section class="tarjeta filtros">
      <label>Promotor <app-selector-promotor [(valor)]="idPromotor" [todos]="true" /></label>
      <label>Desde <input type="date" [(ngModel)]="desde" /></label>
      <label>Hasta <input type="date" [(ngModel)]="hasta" /></label>
      <label>Estado <select [(ngModel)]="estado"><option value="">Todos</option><option>Pendiente</option><option>Revisada</option><option>Sancionada</option></select></label>
      <label class="check"><input type="checkbox" [(ngModel)]="criticas" /> Solo críticas</label>
      <button type="button" class="boton boton--rojo" (click)="cargar()">BUSCAR</button>
      <button type="button" class="boton" (click)="nueva.set(!nueva())">+ Reportar incidencia</button>
    </section>
    @if (nueva()) {
      <section class="tarjeta formulario">
        <h2>Reportar incidencia</h2>
        <p class="nota">Se registrará para el promotor seleccionado arriba.</p>
        <label>Tipo <input [(ngModel)]="tipoNueva" placeholder="Ej. Reporte de encargado de tienda" /></label>
        <label>Descripción <textarea [(ngModel)]="descNueva" rows="3"></textarea></label>
        <label class="check"><input type="checkbox" [(ngModel)]="criticaNueva" /> Crítica</label>
        <button type="button" class="boton boton--rojo" (click)="crear()">GUARDAR</button>
      </section>
    }
    <section class="tarjeta">
      <table class="tabla">
        <thead><tr><th>Fecha</th><th>Promotor</th><th>Tipo</th><th>Descripción</th><th>Estado</th><th>Seguimiento</th></tr></thead>
        <tbody>
          @for (i of lista(); track i.id_incidencia) {
            <tr [class.fila-critica]="i.es_critica">
              <td>{{ i.fecha_hora.slice(0, 10) }} {{ hora(i.fecha_hora) }}</td><td>{{ i.nombre_promotor }}</td>
              <td>{{ i.tipo }}{{ i.es_critica ? ' 🚨' : '' }}<br /><small>{{ i.origen }}</small></td><td>{{ i.descripcion }}</td>
              <td>{{ i.estado }} @if (i.comentario_revision) { <br /><small>{{ i.comentario_revision }}</small> }</td>
              <td class="fila-botones">
                <button type="button" class="boton boton--chico" (click)="cambiar(i, 'Revisada')">Revisada</button>
                <button type="button" class="boton boton--chico" (click)="cambiar(i, 'Sancionada')">Sancionada</button>
              </td>
            </tr>
          } @empty { <tr><td colspan="6">No se encontraron incidencias registradas.</td></tr> }
        </tbody>
      </table>
    </section>
  `,
})
export class IncidenciasPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly idPromotor = signal<number | null>(null);
  readonly lista = signal<Incidencia[]>([]);
  readonly nueva = signal(false);
  readonly hora = hora;
  desde = new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10);
  hasta = hoyIso();
  estado = '';
  criticas = false;
  tipoNueva = '';
  descNueva = '';
  criticaNueva = false;

  ngOnInit() { void this.cargar(); }

  async cargar() {
    const p = new URLSearchParams({ desde: this.desde, hasta: this.hasta });
    if (this.idPromotor()) p.set('id_promotor', String(this.idPromotor()));
    if (this.estado) p.set('estado', this.estado);
    if (this.criticas) p.set('critica', '1');
    try {
      this.lista.set((await firstValueFrom(this.http.get<{ incidencias: Incidencia[] }>(`/api/incidencias?${p}`))).incidencias);
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async cambiar(i: Incidencia, estado: string) {
    const comentario = prompt(`Comentario para marcar como ${estado}:`, i.comentario_revision ?? '') ?? '';
    try {
      await firstValueFrom(this.http.put(`/api/incidencias/${i.id_incidencia}`, { estado, comentario }));
      this.avisos.ok('Incidencia actualizada.');
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async crear() {
    try {
      await firstValueFrom(this.http.post('/api/incidencias', { id_promotor: this.idPromotor(), tipo: this.tipoNueva,
        descripcion: this.descNueva, es_critica: this.criticaNueva }));
      this.avisos.ok('Incidencia registrada.');
      this.nueva.set(false);
      this.tipoNueva = this.descNueva = '';
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
