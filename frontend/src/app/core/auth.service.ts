import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { mensajeError } from './api';
import { ColaService } from './cola.service';
import { RUTA_INICIO, Usuario } from './modelos';

/**
 * Estado de la sesión en el navegador. La sesión real vive en una cookie
 * HttpOnly que solo el servidor lee; aquí se guardan los datos públicos del
 * usuario para la interfaz. Los permisos los decide Flask en cada petición.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly cola = inject(ColaService);

  private readonly usuarioActual = signal<Usuario | null>(null);
  readonly usuario = this.usuarioActual.asReadonly();
  readonly autenticado = computed(() => this.usuarioActual() !== null);

  private consultada = false;
  private consultaEnCurso: Promise<Usuario | null> | null = null;

  asegurarSesion(): Promise<Usuario | null> {
    if (this.consultada) return Promise.resolve(this.usuarioActual());
    if (!this.consultaEnCurso) {
      this.consultaEnCurso = firstValueFrom(this.http.get<{ usuario: Usuario }>('/api/auth/me'))
        .then((r) => r.usuario)
        .catch(() => null)
        .then((u) => {
          this.establecer(u);
          this.consultaEnCurso = null;
          return u;
        });
    }
    return this.consultaEnCurso;
  }

  async iniciarSesion(correo: string, password: string): Promise<Usuario> {
    const r = await firstValueFrom(this.http.post<{ usuario: Usuario }>('/api/auth/login', { correo, password }));
    this.establecer(r.usuario);
    return r.usuario;
  }

  async cambiarPassword(actual: string, nueva: string): Promise<string> {
    const r = await firstValueFrom(this.http.post<{ mensaje: string; usuario: Usuario }>(
      '/api/auth/cambiar-password', { password_actual: actual, password_nueva: nueva }));
    this.establecer(r.usuario);
    return r.mensaje;
  }

  async cerrarSesion(): Promise<void> {
    try {
      await firstValueFrom(this.http.post('/api/auth/logout', {}));
    } finally {
      this.olvidarSesion();
      await this.router.navigateByUrl('/login');
    }
  }

  olvidarSesion(): void {
    this.establecer(null);
  }

  rutaInicio(u: Usuario): string {
    return u.debe_cambiar_password ? '/cambiar-password' : RUTA_INICIO[u.rol];
  }

  static mensajeDeError(err: unknown): string {
    return mensajeError(err);
  }

  private establecer(u: Usuario | null) {
    this.usuarioActual.set(u);
    this.consultada = true;
    if (u?.rol === 'Promotor') {
      void this.cola.activar(u.id_usuario);
    } else {
      this.cola.desactivar();
    }
  }
}
