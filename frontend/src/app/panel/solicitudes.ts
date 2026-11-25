import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { hora, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { SolicitudAjuste } from '../core/modelos';

/** Solicitudes de ajuste de los promotores (RF-15, etapa 3): el supervisor aprueba o rechaza. */
@Component({
  selector: 'app-solicitudes',
  imports: [FormsModule],
  template: `
    <section class="tarjeta filtros">
      <label>Estado <select [(ngModel)]="estado" (change)="cargar()">
        <option value="Pendiente">Pendientes</option><option value="Aprobada">Aprobadas</option>
        <option value="Rechazada">Rechazadas</option><option value="">Todas</option></select></label>
      <button type="button" class="boton boton--rojo" (click)="cargar()">ACTUALIZAR</button>
    </section>
    <section class="tarjeta">
      <table class="tabla">
        <thead><tr><th>Enviada</th><th>Promotor</th><th>Día</th><th>Tipo</th><th>Tienda</th><th>Motivo</th><th>Estado</th><th>Respuesta</th></tr></thead>
        <tbody>
          @for (s of lista(); track s.id_solicitud) {
            <tr>
              <td>{{ s.fecha_hora_solicitud.slice(0, 10) }} {{ hora(s.fecha_hora_solicitud) }}</td>
              <td>{{ s.nombre_promotor }}</td><td>{{ s.fecha }}</td><td>{{ s.tipo }}</td><td>{{ s.tienda ?? '—' }}</td>
              <td>{{ s.motivo }}</td><td>{{ s.estado }}</td>
              <td>
                @if (s.estado === 'Pendiente') {
                  <input [(ngModel)]="comentarios[s.id_solicitud]" placeholder="Comentario (obligatorio si rechazas)" />
                  <div class="fila-botones">
                    <button type="button" class="boton boton--chico" (click)="responder(s, 'Aprobada')">Aprobar</button>
                    <button type="button" class="boton boton--chico boton--rojo" (click)="responder(s, 'Rechazada')">Rechazar</button>
                  </div>
                } @else {
                  {{ s.revisor }} · {{ s.comentario_respuesta ?? 'sin comentario' }}
                }
              </td>
            </tr>
          } @empty {
            <tr><td colspan="8">No hay solicitudes con este estado.</td></tr>
          }
        </tbody>
      </table>
    </section>
  `,
})
export class SolicitudesPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly hora = hora;
  readonly lista = signal<SolicitudAjuste[]>([]);
  estado = 'Pendiente';
  comentarios: Record<number, string> = {};

  ngOnInit() { void this.cargar(); }

  async cargar() {
    try {
      const q = this.estado ? `?estado=${this.estado}` : '';
      this.lista.set((await firstValueFrom(this.http.get<{ solicitudes: SolicitudAjuste[] }>(`/api/supervision/solicitudes${q}`))).solicitudes);
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async responder(s: SolicitudAjuste, decision: 'Aprobada' | 'Rechazada') {
    try {
      const r = await firstValueFrom(this.http.put<{ mensaje: string }>(`/api/supervision/solicitudes/${s.id_solicitud}`,
        { decision, comentario: this.comentarios[s.id_solicitud] ?? '' }));
      this.avisos.ok(r.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
