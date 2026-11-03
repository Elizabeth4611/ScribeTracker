import { Component, inject } from '@angular/core';

import { AvisosService } from '../core/avisos.service';

@Component({
  selector: 'app-avisos',
  template: `
    <div class="avisos" aria-live="polite">
      @for (a of avisos.lista(); track a.id) {
        <div class="aviso aviso--{{ a.tipo }}" role="status" (click)="avisos.quitar(a.id)">{{ a.texto }}</div>
      }
    </div>
  `,
})
export class AvisosComponent {
  readonly avisos = inject(AvisosService);
}
