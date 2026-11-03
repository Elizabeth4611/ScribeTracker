import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, input, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { PromotorOpcion } from '../core/modelos';

/** Lista de promotores dentro del alcance del usuario (el servidor filtra). */
@Component({
  selector: 'app-selector-promotor',
  imports: [FormsModule],
  template: `
    <select [ngModel]="valor()" (ngModelChange)="valor.set($event)">
      @if (todos()) { <option [ngValue]="null">Todos</option> } @else { <option [ngValue]="null" disabled>Selecciona un promotor</option> }
      @for (p of promotores(); track p.id_usuario) {
        <option [ngValue]="p.id_usuario">{{ p.nombre_completo }} ({{ p.numero_empleado || 's/n' }}){{ p.estatus === 'Inactivo' ? ' · inactivo' : '' }}</option>
      }
    </select>
  `,
})
export class SelectorPromotor implements OnInit {
  private readonly http = inject(HttpClient);
  readonly valor = model<number | null>(null);
  readonly todos = input(false);
  readonly promotores = signal<PromotorOpcion[]>([]);

  async ngOnInit() {
    const r = await firstValueFrom(this.http.get<{ promotores: PromotorOpcion[] }>('/api/supervision/promotores'));
    this.promotores.set(r.promotores);
  }
}
