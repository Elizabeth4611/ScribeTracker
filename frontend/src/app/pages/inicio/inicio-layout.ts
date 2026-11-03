import { Component, inject, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from '../../core/auth.service';

/** Marco común de las pantallas iniciales: encabezado y cierre de sesión. */
@Component({
  selector: 'app-inicio-layout',
  imports: [RouterOutlet],
  template: `
    <header class="barra">
      <span class="marca">ScribeTracker</span>
      @if (auth.usuario(); as usuario) {
        <div class="barra__usuario">
          <span>{{ usuario.nombre_completo }}</span>
          <span class="insignia">{{ usuario.rol }}</span>
          <button type="button" class="boton" (click)="salir()" [disabled]="saliendo()">
            {{ saliendo() ? 'Saliendo…' : 'Cerrar sesión' }}
          </button>
        </div>
      }
    </header>
    <main class="contenido">
      <router-outlet />
    </main>
  `,
})
export class InicioLayout {
  readonly auth = inject(AuthService);
  readonly saliendo = signal(false);

  async salir(): Promise<void> {
    this.saliendo.set(true);
    try {
      await this.auth.cerrarSesion();
    } finally {
      this.saliendo.set(false);
    }
  }
}
