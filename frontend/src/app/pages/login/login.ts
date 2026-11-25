import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';

/**
 * Inicio de sesión (etapa 3). Se acepta el correo (ERS, modelo de diseño) o
 * el número de empleado (prototipos) en el mismo campo. Tras 3 intentos
 * fallidos la cuenta se bloquea 15 minutos (el servidor responde 423).
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
            <span>CORREO O NÚMERO DE EMPLEADO:</span>
            <input type="text" formControlName="usuario" autocomplete="username" autocapitalize="off" spellcheck="false" required />
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
    usuario: ['', Validators.required],
    password: ['', Validators.required],
  });
  readonly enviando = signal(false);
  readonly error = signal<string | null>(null);

  async enviar(): Promise<void> {
    if (this.form.invalid) {
      this.error.set('Escribe tu correo o número de empleado y tu contraseña.');
      return;
    }
    this.enviando.set(true);
    this.error.set(null);
    const { usuario, password } = this.form.getRawValue();
    try {
      const u = await this.auth.iniciarSesion(usuario.trim(), password);
      await this.router.navigateByUrl(this.auth.rutaInicio(u));
    } catch (err) {
      this.error.set(AuthService.mensajeDeError(err));
      this.form.controls.password.reset();
    } finally {
      this.enviando.set(false);
    }
  }
}
