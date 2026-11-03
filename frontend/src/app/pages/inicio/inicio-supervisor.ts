import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';

import { AuthService } from '../../core/auth.service';
import { InicioSupervisor } from '../../core/modelos';

@Component({
  selector: 'app-inicio-supervisor',
  template: `
    <h1>Inicio de Supervisor</h1>
    @if (error()) {
      <p class="alerta" role="alert">{{ error() }}</p>
    } @else if (datos(); as d) {
      <section class="tarjeta">
        <h2>Bienvenido, {{ d.usuario.nombre_completo }}</h2>
        <h3>Promotores a tu cargo ({{ d.promotores.length }})</h3>
        @if (d.promotores.length === 0) {
          <p class="sutil">Aún no tienes promotores asignados.</p>
        } @else {
          <table class="tabla">
            <thead>
              <tr><th>Nombre</th><th>Correo</th><th>Estatus</th></tr>
            </thead>
            <tbody>
              @for (p of d.promotores; track p.id_usuario) {
                <tr>
                  <td>{{ p.nombre_completo }}</td>
                  <td>{{ p.correo_electronico }}</td>
                  <td>
                    <span class="insignia" [class.insignia--apagada]="p.estatus === 'Inactivo'">{{ p.estatus }}</span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>
    } @else {
      <p class="sutil">Cargando…</p>
    }
  `,
})
export class InicioSupervisorPage {
  readonly datos = signal<InicioSupervisor | null>(null);
  readonly error = signal<string | null>(null);

  constructor() {
    inject(HttpClient)
      .get<InicioSupervisor>('/api/inicio/supervisor')
      .subscribe({
        next: (d) => this.datos.set(d),
        error: (e) => this.error.set(AuthService.mensajeDeError(e)),
      });
  }
}
