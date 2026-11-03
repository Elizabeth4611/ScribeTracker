import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';

import { AuthService } from '../../core/auth.service';
import { Estatus, InicioAdministrador, Rol } from '../../core/modelos';

@Component({
  selector: 'app-inicio-administrador',
  template: `
    <h1>Inicio de Administrador</h1>
    @if (error()) {
      <p class="alerta" role="alert">{{ error() }}</p>
    } @else if (datos(); as d) {
      <section class="tarjeta">
        <h2>Bienvenido, {{ d.usuario.nombre_completo }}</h2>
        <h3>Usuarios registrados: {{ d.total_usuarios }}</h3>
        <table class="tabla">
          <thead>
            <tr><th>Rol</th><th>Activos</th><th>Inactivos</th></tr>
          </thead>
          <tbody>
            @for (rol of roles; track rol) {
              <tr>
                <td>{{ rol }}</td>
                @for (estatus of listaEstatus; track estatus) {
                  <td>{{ d.resumen_usuarios[rol][estatus] }}</td>
                }
              </tr>
            }
          </tbody>
        </table>
      </section>
    } @else {
      <p class="sutil">Cargando…</p>
    }
  `,
})
export class InicioAdministradorPage {
  readonly roles: Rol[] = ['Promotor', 'Supervisor', 'Administrador'];
  readonly listaEstatus: Estatus[] = ['Activo', 'Inactivo'];

  readonly datos = signal<InicioAdministrador | null>(null);
  readonly error = signal<string | null>(null);

  constructor() {
    inject(HttpClient)
      .get<InicioAdministrador>('/api/inicio/administrador')
      .subscribe({
        next: (d) => this.datos.set(d),
        error: (e) => this.error.set(AuthService.mensajeDeError(e)),
      });
  }
}
