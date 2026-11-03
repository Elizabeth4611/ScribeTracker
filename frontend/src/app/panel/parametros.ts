import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Parametro } from '../core/modelos';

/** Parámetros globales (ERS 3.1, portal admin punto 7). */
@Component({
  selector: 'app-parametros',
  imports: [FormsModule],
  template: `
    <section class="tarjeta">
      <input type="search" class="busqueda" placeholder="🔍 Buscar parámetro…" [(ngModel)]="q" (input)="cargar()" />
      <table class="tabla">
        <thead><tr><th>Categoría</th><th>Parámetro</th><th>Valor</th><th>Rango</th><th>Por defecto</th><th></th></tr></thead>
        <tbody>
          @for (p of lista(); track p.clave) {
            <tr>
              <td>{{ p.categoria }}</td><td>{{ p.descripcion }}<br /><small>{{ p.clave }}</small></td>
              <td><input class="entrada-chica" [(ngModel)]="valores[p.clave]" /></td>
              <td>{{ p.rango || '—' }}</td><td>{{ p.valor_default }}</td>
              <td class="fila-botones">
                <button type="button" class="boton boton--chico" (click)="guardar(p)" [disabled]="valores[p.clave] === p.valor_activo">Guardar</button>
                <button type="button" class="boton boton--chico" (click)="restablecer(p)">Restablecer</button>
              </td>
            </tr>
          }
        </tbody>
      </table>
      <p class="nota">Las tolerancias de 20 min (retardo, entrevista P16) y 30 min (alerta sin llegada, RF-11) quedan separadas hasta que se confirme cuál aplica.</p>
    </section>
  `,
})
export class ParametrosPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly lista = signal<Parametro[]>([]);
  valores: Record<string, string> = {};
  q = '';

  ngOnInit() { void this.cargar(); }

  async cargar() {
    const r = await firstValueFrom(this.http.get<{ parametros: Parametro[] }>(`/api/parametros?q=${encodeURIComponent(this.q)}`));
    this.lista.set(r.parametros);
    r.parametros.forEach((p) => (this.valores[p.clave] = p.valor_activo));
  }

  async guardar(p: Parametro) {
    try {
      const r = await firstValueFrom(this.http.put<{ mensaje: string }>(`/api/parametros/${p.clave}`, { valor: this.valores[p.clave] }));
      this.avisos.ok(r.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async restablecer(p: Parametro) {
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string }>(`/api/parametros/${p.clave}/restablecer`, {}));
      this.avisos.ok(r.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
