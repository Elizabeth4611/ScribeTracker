import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { AvisosService } from '../../core/avisos.service';

@Component({
  selector: 'app-cambiar-password',
  imports: [FormsModule],
  template: `
    <main class="acceso">
      <section class="acceso__caja">
        <div class="marca-grande"><span class="logo">Scribe</span> ScribeTracker</div>
        <h1 class="titulo-centro">CAMBIAR CONTRASEÑA</h1>
        @if (auth.usuario()?.debe_cambiar_password) {
          <p class="nota">Tu contraseña es temporal. Elige una nueva para continuar.</p>
        }
        <label class="campo"><span>Contraseña actual:</span>
          <input type="password" [(ngModel)]="actual" name="actual" autocomplete="current-password" /></label>
        <label class="campo"><span>Nueva contraseña (mínimo 8, letras y números):</span>
          <input type="password" [(ngModel)]="nueva" name="nueva" autocomplete="new-password" /></label>
        <label class="campo"><span>Repite la nueva contraseña:</span>
          <input type="password" [(ngModel)]="repetida" name="repetida" autocomplete="new-password" /></label>
        @if (error()) { <p class="alerta">{{ error() }}</p> }
        <button type="button" class="boton boton--rojo" (click)="guardar()" [disabled]="enviando()">GUARDAR</button>
        @if (!auth.usuario()?.debe_cambiar_password) {
          <button type="button" class="boton" (click)="volver()">CANCELAR</button>
        }
      </section>
    </main>
  `,
})
export class CambiarPasswordPage {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly avisos = inject(AvisosService);
  actual = '';
  nueva = '';
  repetida = '';
  readonly error = signal<string | null>(null);
  readonly enviando = signal(false);

  async guardar() {
    if (this.nueva !== this.repetida) {
      this.error.set('Las contraseñas nuevas no coinciden.');
      return;
    }
    this.enviando.set(true);
    try {
      this.avisos.ok(await this.auth.cambiarPassword(this.actual, this.nueva));
      this.volver();
    } catch (e) {
      this.error.set(AuthService.mensajeDeError(e));
    } finally {
      this.enviando.set(false);
    }
  }

  volver() {
    const u = this.auth.usuario();
    void this.router.navigateByUrl(u ? this.auth.rutaInicio(u) : '/login');
  }
}
