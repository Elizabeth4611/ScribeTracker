import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { Rol } from './modelos';

/*
 * Los guards solo mejoran la navegación. La seguridad real está en el
 * servidor: aunque alguien se salte un guard, Flask responde 401/403.
 */

export const soloInvitadosGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const u = await auth.asegurarSesion();
  return u ? router.parseUrl(auth.rutaInicio(u)) : true;
};

export const cambioPasswordGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const u = await auth.asegurarSesion();
  return u ? true : router.parseUrl('/login');
};

export function rolesGuard(...roles: Rol[]): CanActivateFn {
  return async () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const u = await auth.asegurarSesion();
    if (!u) return router.parseUrl('/login');
    if (u.debe_cambiar_password) return router.parseUrl('/cambiar-password');
    return roles.includes(u.rol) ? true : router.parseUrl(auth.rutaInicio(u));
  };
}

export const irAInicioGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const u = await auth.asegurarSesion();
  return router.parseUrl(u ? auth.rutaInicio(u) : '/login');
};
