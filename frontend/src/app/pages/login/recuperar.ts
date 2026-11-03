import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

/**
 * Prototipo "Recupera tu contraseña". El envío de enlaces requiere un
 * servidor de correo (SMTP) que no está configurado; el administrador
 * genera una contraseña temporal desde Gestión de usuarios.
 */
@Component({
  selector: 'app-recuperar',
  imports: [FormsModule, RouterLink],
  template: `
    <main class="acceso">
      <section class="acceso__caja">
        <div class="marca-grande"><span class="logo">Scribe</span> ScribeTracker</div>
        <h1 class="titulo-centro">RECUPERA TU CONTRASEÑA</h1>
        <p>Ingresa tu correo electrónico para restablecer tu contraseña.</p>
        <label class="campo"><span>Correo electrónico:</span>
          <input type="email" [(ngModel)]="correo" name="correo" /></label>
        @if (mensaje()) { <p class="nota">{{ mensaje() }}</p> }
        <button type="button" class="boton boton--rojo" (click)="enviar()" [disabled]="!correo">Enviar enlace</button>
        <a routerLink="/login" class="enlace">← volver al inicio</a>
      </section>
    </main>
  `,
})
export class RecuperarPage {
  private readonly http = inject(HttpClient);
  correo = '';
  readonly mensaje = signal<string | null>(null);

  async enviar() {
    const r = await firstValueFrom(this.http.post<{ mensaje: string }>('/api/auth/recuperar', { correo: this.correo }));
    this.mensaje.set(r.mensaje + ' (El envío por correo no está configurado en esta versión.)');
  }
}
