import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { duracion, fechaLarga, hora, hoyIso, mensajeError } from '../core/api';
import { ResumenDia } from '../core/modelos';

/** Historial propio por fecha (RF-07). */
@Component({
  selector: 'app-historial',
  imports: [FormsModule],
  template: `
    <label class="campo campo--fila"><span>Fecha:</span>
      <input type="date" [(ngModel)]="fecha" (change)="cargar()" [max]="hoy" /></label>
    @if (error()) { <p class="alerta">{{ error() }}</p> }
    @if (datos(); as d) {
      <p class="nota">{{ fechaLarga(d.fecha) }}</p>
      <section class="resumen-dia">
        <h2>RESUMEN DEL DÍA</h2>
        <p>📊 Tiendas visitadas: <b>{{ d.resumen.tiendas_visitadas }}</b> de {{ d.resumen.tiendas_asignadas }}</p>
        <p>⏰ Horas en tienda: <b>{{ duracion(d.resumen.minutos_en_tienda) }}</b></p>
        <p>⏯ Pausas: <b>{{ duracion(d.resumen.minutos_en_pausa) }}</b> ({{ d.jornada?.pausas?.length ?? 0 }})</p>
        @if (d.jornada) { <p>Jornada: {{ hora(d.jornada.inicio) }} – {{ hora(d.jornada.fin) }} · {{ d.jornada.estado }}</p> }
      </section>
      <h2 class="subtitulo">HISTORIAL:</h2>
      @for (a of d.asignaciones; track a.id_asignacion) {
        <article class="tarjeta-roja">
          <p>TIENDA: {{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}</p>
          @if (a.visita) {
            <p>HORARIO: {{ hora(a.visita.checkin) }} – {{ hora(a.visita.checkout) }} @if (a.visita.duracion_min != null) { ({{ duracion(a.visita.duracion_min) }}) }</p>
            <div class="galeria galeria--chica">
              @for (e of a.visita.evidencias; track e.id_evidencia) {
                <figure [class.mala]="e.estatus_validacion !== 'Válida'">
                  <img [src]="e.url" [alt]="e.categoria" loading="lazy" />
                  <figcaption>{{ e.categoria }} · {{ hora(e.fecha_hora_captura) }}</figcaption>
                </figure>
              }
            </div>
          } @else {
            <p>Sin visita registrada.</p>
          }
        </article>
      } @empty {
        <p class="nota">No hay tiendas asignadas en esta fecha.</p>
      }
    }
  `,
})
export class HistorialPage implements OnInit {
  private readonly http = inject(HttpClient);
  readonly hoy = hoyIso();
  fecha = hoyIso();
  readonly datos = signal<ResumenDia | null>(null);
  readonly error = signal<string | null>(null);
  readonly hora = hora;
  readonly duracion = duracion;
  readonly fechaLarga = fechaLarga;

  ngOnInit() { void this.cargar(); }

  async cargar() {
    try {
      this.error.set(null);
      this.datos.set(await firstValueFrom(this.http.get<ResumenDia>(`/api/promotor/historial?fecha=${this.fecha}`)));
    } catch (e) {
      this.error.set(mensajeError(e));
    }
  }
}
