import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';

import { AuthService } from '../../core/auth.service';
import { InicioPromotor } from '../../core/modelos';

@Component({
  selector: 'app-inicio-promotor',
  template: `
    <h1>Inicio de Promotor</h1>
    @if (error()) {
      <p class="alerta" role="alert">{{ error() }}</p>
    } @else if (datos(); as d) {
      <section class="tarjeta">
        <h2>Bienvenido, {{ d.usuario.nombre_completo }}</h2>
        <dl class="datos">
          <dt>Correo</dt><dd>{{ d.usuario.correo_electronico }}</dd>
          <dt>Teléfono</dt><dd>{{ d.usuario.telefono || 'Sin registrar' }}</dd>
          <dt>Supervisor</dt>
          <dd>
            @if (d.supervisor; as s) {
              {{ s.nombre_completo }} ({{ s.correo_electronico }})
            } @else {
              Sin supervisor asignado
            }
          </dd>
        </dl>
      </section>
    } @else {
      <p class="sutil">Cargando…</p>
    }
  `,
})
export class InicioPromotorPage {
  readonly datos = signal<InicioPromotor | null>(null);
  readonly error = signal<string | null>(null);

  constructor() {
    inject(HttpClient)
      .get<InicioPromotor>('/api/inicio/promotor')
      .subscribe({
        next: (d) => this.datos.set(d),
        error: (e) => this.error.set(AuthService.mensajeDeError(e)),
      });
  }
}
