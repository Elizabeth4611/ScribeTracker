import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PromotorService } from './promotor.service';

@Component({
  selector: 'app-inicio-promotor',
  imports: [RouterLink],
  template: `
    <h1 class="bienvenida">¡BIENVENIDO!</h1>
    <p class="estado-linea">
      Estado: <span class="punto" [class.punto--verde]="ps.jornadaAbierta() && !ps.enPausa()"></span>
      {{ ps.hoy()?.estado?.estado_jornada ?? '…' }}
      @if (ps.hoy()?.estado?.tienda_actual) { · {{ ps.hoy()?.estado?.tienda_actual }} }
    </p>
    <div class="mosaico">
      <a routerLink="/promotor/jornada" class="mosaico__item"><span>⌂</span>Entrada/salida</a>
      <a routerLink="/promotor/historial" class="mosaico__item"><span>✔</span>Historial</a>
      <a routerLink="/promotor/pausas" class="mosaico__item"><span>⏸</span>Pausas</a>
      <a routerLink="/promotor/configuracion" class="mosaico__item"><span>⚙</span>Configuración</a>
    </div>
  `,
})
export class InicioPromotor {
  readonly ps = inject(PromotorService);
}
