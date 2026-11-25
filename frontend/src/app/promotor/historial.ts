import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { duracion, fechaLarga, hora, hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { ResumenDia, SolicitudAjuste, TIPOS_SOLICITUD } from '../core/modelos';

/** Historial propio por fecha (RF-07) y solicitudes de ajuste (RF-15, etapa 3). */
@Component({
  selector: 'app-historial',
  imports: [FormsModule],
  styles: [`.solicitud.aprobada { border-left: 6px solid #16a34a; } .solicitud.rechazada { border-left: 6px solid #9ca3af; opacity: .9; }`],
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

      <h2 class="subtitulo">SOLICITAR AJUSTE</h2>
      @if (!formulario()) {
        <button type="button" class="boton boton--rojo" (click)="formulario.set(true)">SOLICITAR AJUSTE DE ESTE DÍA</button>
        <p class="nota">Si olvidaste el check-out, una tienda estaba cerrada o un horario quedó mal, pide el ajuste a tu supervisor.</p>
      } @else {
        <section class="tarjeta-oscura">
          <label class="campo"><span>Tipo de ajuste:</span>
            <select [(ngModel)]="tipo">@for (t of tipos; track t) { <option [value]="t">{{ t }}</option> }</select></label>
          <label class="campo"><span>Tienda (opcional):</span>
            <select [(ngModel)]="idAsignacion">
              <option [ngValue]="null">Ninguna en particular</option>
              @for (a of d.asignaciones; track a.id_asignacion) { <option [ngValue]="a.id_asignacion">{{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}</option> }
            </select></label>
          <label class="campo"><span>Motivo (10 a 300 caracteres):</span>
            <textarea [(ngModel)]="motivo" rows="3" maxlength="300"></textarea></label>
          <small class="nota">{{ motivo.trim().length }}/300</small>
          <div class="fila-botones">
            <button type="button" class="boton" (click)="formulario.set(false)">CANCELAR</button>
            <button type="button" class="boton boton--rojo" (click)="solicitar()" [disabled]="enviando()">ENVIAR SOLICITUD</button>
          </div>
        </section>
      }
    }

    <h2 class="subtitulo">MIS SOLICITUDES</h2>
    @for (s of solicitudes(); track s.id_solicitud) {
      <article class="tarjeta-roja solicitud" [class.aprobada]="s.estado === 'Aprobada'" [class.rechazada]="s.estado === 'Rechazada'">
        <p><b>{{ s.tipo }}</b> · {{ s.fecha }} @if (s.tienda) { · {{ s.tienda }} }</p>
        <p>{{ s.motivo }}</p>
        <p class="etiqueta" [class.etiqueta--ok]="s.estado === 'Aprobada'" [class.etiqueta--pendiente]="s.estado === 'Pendiente'">{{ s.estado }}</p>
        @if (s.comentario_respuesta) { <p><small>Supervisor: {{ s.comentario_respuesta }}</small></p> }
      </article>
    } @empty {
      <p class="nota">Aún no has enviado solicitudes de ajuste.</p>
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

  private readonly avisos = inject(AvisosService);
  readonly tipos = TIPOS_SOLICITUD;
  readonly formulario = signal(false);
  readonly enviando = signal(false);
  readonly solicitudes = signal<SolicitudAjuste[]>([]);
  tipo: string = 'Tienda no visitada';
  idAsignacion: number | null = null;
  motivo = '';

  ngOnInit() { void this.cargar(); void this.cargarSolicitudes(); }

  async cargarSolicitudes() {
    try {
      this.solicitudes.set((await firstValueFrom(this.http.get<{ solicitudes: SolicitudAjuste[] }>('/api/promotor/solicitudes'))).solicitudes);
    } catch { /* sin conexión: se conserva la lista */ }
  }

  async solicitar() {
    this.enviando.set(true);
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string }>('/api/promotor/solicitudes',
        { tipo: this.tipo, motivo: this.motivo, fecha: this.fecha, id_asignacion: this.idAsignacion }));
      this.avisos.ok(r.mensaje);
      this.formulario.set(false);
      this.motivo = '';
      this.idAsignacion = null;
      await this.cargarSolicitudes();
    } catch (e) {
      this.avisos.error(mensajeError(e));
    } finally {
      this.enviando.set(false);
    }
  }

  async cargar() {
    try {
      this.error.set(null);
      this.datos.set(await firstValueFrom(this.http.get<ResumenDia>(`/api/promotor/historial?fecha=${this.fecha}`)));
    } catch (e) {
      this.error.set(mensajeError(e));
    }
  }
}
