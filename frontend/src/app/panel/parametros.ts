import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Parametro } from '../core/modelos';

/** Parámetros: las reglas del sistema que el administrador puede ajustar. */
@Component({
  selector: 'app-parametros',
  imports: [FormsModule],
  template: `
    <section class="tarjeta">
      <h2>⚙ PARÁMETROS DEL SISTEMA</h2>
      <p class="nota">Aquí se ajustan las reglas con las que trabaja ScribeTracker: horarios, pausas, alertas, ubicación y seguridad.
        Los cambios se aplican de inmediato para todos los usuarios. Si algo no queda bien, usa «Restablecer» para volver al valor original.</p>
      <input type="search" class="busqueda" placeholder="🔍 Buscar parámetro…" [(ngModel)]="q" (input)="cargar()" />
      @for (g of grupos(); track g.categoria) {
        <h3 class="param-grupo">{{ g.categoria }}</h3>
        <div class="param-lista">
          @for (p of g.items; track p.clave) {
            <div class="param">
              <div class="param__texto">
                <b>{{ p.descripcion }}</b>
                <small>{{ p.ayuda }}</small>
                <small class="param__extra">Valor original: {{ p.valor_default }} {{ unidadCorta(p) }}@if (p.rango) { · permitido de {{ rango(p) }} }</small>
              </div>
              <div class="param__valor">
                <input class="entrada-chica" [type]="p.tipo_dato === 'hora' ? 'text' : 'number'" [attr.placeholder]="p.tipo_dato === 'hora' ? 'HH:MM' : null" [attr.maxlength]="p.tipo_dato === 'hora' ? 5 : null" [(ngModel)]="valores[p.clave]" />
                <span>{{ p.tipo_dato === 'hora' ? '(24 h)' : unidadCorta(p) }}</span>
              </div>
              <div class="fila-botones">
                <button type="button" class="boton boton--chico boton--rojo" (click)="guardar(p)" [disabled]="String(valores[p.clave]) === p.valor_activo">Guardar</button>
                <button type="button" class="boton boton--chico" (click)="restablecer(p)" [disabled]="p.valor_activo === p.valor_default">Restablecer</button>
              </div>
            </div>
          }
        </div>
      } @empty { <p class="nota">Sin resultados.</p> }
    </section>
  `,
  styles: [`
    .param-grupo { margin: 1.2rem 0 .4rem; font-size: 1rem; border-bottom: 2px solid var(--rojo); padding-bottom: .2rem; }
    .param { display: grid; grid-template-columns: 1fr auto auto; gap: .8rem; align-items: center; padding: .6rem 0; border-bottom: 1px solid #e5e5e5; }
    .param__texto { display: grid; gap: .15rem; }
    .param__texto small { color: #444; }
    .param__extra { color: #777 !important; }
    .param__valor { display: flex; align-items: center; gap: .3rem; white-space: nowrap; }
    .param__valor input { width: 6.5rem; }
    @media (max-width: 700px) { .param { grid-template-columns: 1fr; } }
  `],
})
export class ParametrosPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly lista = signal<Parametro[]>([]);
  /** Parámetros agrupados por tema, en el orden que manda el servidor. */
  readonly grupos = computed(() => {
    const g: { categoria: string; items: Parametro[] }[] = [];
    for (const p of this.lista()) {
      const ult = g[g.length - 1];
      if (ult && ult.categoria === p.categoria) ult.items.push(p); else g.push({ categoria: p.categoria, items: [p] });
    }
    return g;
  });
  valores: Record<string, string | number> = {};
  readonly String = String;
  q = '';

  ngOnInit() { void this.cargar(); }

  async cargar() {
    const r = await firstValueFrom(this.http.get<{ parametros: Parametro[] }>(`/api/parametros?q=${encodeURIComponent(this.q)}`));
    this.lista.set(r.parametros);
    r.parametros.forEach((p) => (this.valores[p.clave] = p.valor_activo));
  }

  unidadCorta(p: Parametro): string { return p.unidad === 'hora' ? '' : p.unidad; }

  rango(p: Parametro): string { return `${(p.rango ?? '').replace('-', ' a ')} ${this.unidadCorta(p)}`.trim(); }

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
