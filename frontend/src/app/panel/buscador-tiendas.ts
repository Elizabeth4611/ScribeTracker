import { HttpClient } from '@angular/common/http';
import { Component, inject, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { Tienda } from '../core/modelos';

/** Busca tiendas activas para agregarlas a una ruta o asignación. */
@Component({
  selector: 'app-buscador-tiendas',
  imports: [FormsModule],
  template: `
    <div class="buscador">
      <input type="search" placeholder="🔍 Buscar tienda por nombre o cadena…" [(ngModel)]="q" (input)="buscar()" />
      @if (resultados().length) {
        <ul class="sugerencias">
          @for (t of resultados(); track t.id_tienda) {
            <li><button type="button" (click)="elegir(t)">+ {{ t.nombre_comercial }} {{ t.sucursal }} <small>{{ t.cadena }} · {{ t.zona || 'sin zona' }}</small></button></li>
          }
        </ul>
      }
    </div>
  `,
})
export class BuscadorTiendas {
  private readonly http = inject(HttpClient);
  readonly elegida = output<Tienda>();
  readonly resultados = signal<Tienda[]>([]);
  q = '';
  private t?: ReturnType<typeof setTimeout>;

  buscar() {
    clearTimeout(this.t);
    this.t = setTimeout(async () => {
      const r = await firstValueFrom(this.http.get<{ tiendas: Tienda[] }>(
        `/api/tiendas?estatus=Activa&por_pagina=15&q=${encodeURIComponent(this.q)}`));
      this.resultados.set(r.tiendas);
    }, 250);
  }

  elegir(t: Tienda) {
    this.elegida.emit(t);
    this.resultados.set([]);
    this.q = '';
  }
}
