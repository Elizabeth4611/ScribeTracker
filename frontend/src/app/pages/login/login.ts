import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';

/**
 * Inicio de sesión. Los prototipos piden "ID de empleado"; el ERS y el
 * modelo de diseño (RF-01) piden correo electrónico. Se mantiene el correo
 * (decisión documentada en docs/MATRIZ_REQUISITOS.md).
 */
@Component({
  selector: 'app-login',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <main class="acceso">
      <section class="acceso__caja">
        <div class="marca-grande"><span class="logo">Scribe</span> ScribeTracker</div>
        <form [formGroup]="form" (ngSubmit)="enviar()" novalidate>
          <label class="campo">
            <span>CORREO ELECTRÓNICO:</span>
            <input type="email" formControlName="correo" autocomplete="username" required />
          </label>
          <label class="campo">
            <span>CONTRASEÑA:</span>
            <input type="password" formControlName="password" autocomplete="current-password" required />
          </label>
          <a routerLink="/recuperar" class="enlace">¿Olvidaste tu contraseña?</a>
          @if (error()) { <p class="alerta" role="alert">{{ error() }}</p> }
          <button type="submit" class="boton boton--rojo boton--grande" [disabled]="enviando()">
            {{ enviando() ? 'ENTRANDO…' : 'ENTRAR' }}
          </button>
        </form>
      </section>
    </main>
  `,
})
export class LoginPage {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly fb = inject(NonNullableFormBuilder);

  readonly form = this.fb.group({
    correo: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });
  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);

  async enviar(): Promise<void> {
    if (this.form.invalid) {
      this.error.set('Escribe un correo válido y tu contraseña.');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    const { correo, password } = this.form.getRawValue();
    try {
      const u = await this.auth.iniciarSesion(correo, password);
      await this.router.navigateByUrl(this.auth.rutaInicio(u));
    } catch (err) {
      this.error.set(AuthService.mensajeDeError(err));
      this.form.controls.password.reset();
    } finally {
      this.enviando.set(false);
    }
  }
}
