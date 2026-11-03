import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { ReporteInfo } from '../core/modelos';
import { SelectorPromotor } from './selector-promotor';

/** Reportes diarios, semanales y mensuales (RF-13, RF-15, RF-17) y exportación PDF (RF-16). */
@Component({
  selector: 'app-reportes',
  imports: [FormsModule, SelectorPromotor],
  template: `
    <section class="tarjeta formulario-linea">
      <h2>📊 REPORTES DE ACTIVIDAD</h2>
      <label>Fecha de referencia <input type="date" [(ngModel)]="fecha" /></label>
      <label>Promotor <app-selector-promotor [(valor)]="idPromotor" [todos]="true" /></label>
      <label>Tipo <select [(ngModel)]="tipo"><option>Diario</option><option>Semanal</option><option>Mensual</option></select></label>
      <label>Contenido <select [(ngModel)]="contenido"><option>Desempeño</option><option>Incidencias</option><option>Exhibición</option></select></label>
      <button type="button" class="boton boton--rojo" (click)="generar()" [disabled]="generando()">📊 GENERAR REPORTE</button>
      <p class="nota">Semanal: de lunes a domingo de la semana de la fecha. Mensual: mes completo. "Exhibición" incluye las fotos válidas de anaquel, precios y promociones.</p>
    </section>
    @if (metricas(); as m) {
      <section class="tarjeta">
        <h2>Vista previa: {{ m.contenido }} · {{ m.tipo }} del {{ m.desde }} al {{ m.hasta }}</h2>
        <p>Promotores: {{ m.totales.promotores }} · Visitadas {{ m.totales.tiendas_visitadas }}/{{ m.totales.tiendas_asignadas }}
          ({{ m.totales.cumplimiento_pct ?? '—' }} %) · Incidencias {{ m.totales.incidencias }} ({{ m.totales.incidencias_criticas }} críticas) · Fotos válidas {{ m.totales.fotos_validas }}</p>
        <table class="tabla tabla--chica">
          <tr><th>Promotor</th><th>Visitadas/asignadas</th><th>Cumplimiento</th><th>Tiempo prom.</th><th>Retardos</th><th>Incidencias</th><th>Fotos válidas</th></tr>
          @for (p of m.promotores; track p.id_promotor) {
            <tr><td>{{ p.nombre }}</td><td>{{ p.tiendas_visitadas }}/{{ p.tiendas_asignadas }}</td><td>{{ p.cumplimiento_pct ?? '—' }} %</td>
              <td>{{ p.tiempo_promedio_tienda_min ?? '—' }} min</td><td>{{ p.retardos }}</td><td>{{ p.incidencias_total }}</td><td>{{ p.fotos_validas }}/{{ p.fotos_total }}</td></tr>
          }
        </table>
      </section>
    }
    <section class="tarjeta">
      <h2>REPORTES</h2>
      <table class="tabla">
        <thead><tr><th>Nombre</th><th>Periodo</th><th>Promotor</th><th>Generado</th><th>Exportar</th></tr></thead>
        <tbody>
          @for (r of lista(); track r.id_reporte) {
            <tr>
              <td>Reporte {{ r.contenido.toLowerCase() }} · {{ r.tipo }}</td><td>{{ r.desde }} – {{ r.hasta }}</td><td>{{ r.promotor }}</td>
              <td>{{ r.fecha_generacion.replace('T', ' ').slice(0, 16) }}<br /><small>{{ r.generado_por }}</small></td>
              <td><a class="boton boton--chico" [href]="'/api/reportes/' + r.id_reporte + '/pdf'">PDF</a>
                <button type="button" class="boton boton--chico" disabled title="Excel no forma parte de RF-16; ver matriz de requisitos">EXCEL</button></td>
            </tr>
          } @empty { <tr><td colspan="5">No hay reportes disponibles.</td></tr> }
        </tbody>
      </table>
    </section>
  `,
})
export class ReportesPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly idPromotor = signal<number | null>(null);
  readonly lista = signal<ReporteInfo[]>([]);
  readonly metricas = signal<any>(null);
  readonly generando = signal(false);
  fecha = hoyIso();
  tipo = 'Semanal';
  contenido = 'Desempeño';

  ngOnInit() { void this.cargar(); }

  async cargar() {
    this.lista.set((await firstValueFrom(this.http.get<{ reportes: ReporteInfo[] }>('/api/reportes'))).reportes);
  }

  async generar() {
    this.generando.set(true);
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string; metricas: any }>('/api/reportes', {
        tipo: this.tipo, contenido: this.contenido, fecha: this.fecha, id_promotor: this.idPromotor() ?? 'todos' }));
      this.metricas.set(r.metricas);
      this.avisos.ok(r.mensaje + ' Puedes descargarlo en PDF en la lista.');
      await this.cargar();
    } catch (e) {
      this.avisos.error(mensajeError(e));
    } finally {
      this.generando.set(false);
    }
  }
}
