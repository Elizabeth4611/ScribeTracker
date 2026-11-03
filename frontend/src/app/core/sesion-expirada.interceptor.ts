import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthService } from './auth.service';

/** Rutas cuyo 401 es una respuesta normal y no una sesión vencida. */
const SIN_REDIRECCION = ['/api/auth/login', '/api/auth/me', '/api/auth/cambiar-password'];

/**
 * 401: sesión cerrada, usuario desactivado o contraseña cambiada → login.
 * 403 con codigo "cambiar_password": debe cambiar la contraseña temporal.
 * Las acciones del promotor que vienen de la cola sin conexión no
 * redirigen: quedan pendientes hasta que vuelva a iniciar sesión.
 */
export const sesionExpiradaInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && !SIN_REDIRECCION.some((r) => req.url.startsWith(r))) {
        if (err.status === 401 && !req.headers.has('X-Id-Cliente')) {
          auth.olvidarSesion();
          void router.navigateByUrl('/login');
        } else if (err.status === 403 && (err.error as { codigo?: string })?.codigo === 'cambiar_password') {
          void router.navigateByUrl('/cambiar-password');
        }
      }
      return throwError(() => err);
    }),
  );
};
