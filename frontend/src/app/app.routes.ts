import { Routes } from '@angular/router';

import { cambioPasswordGuard, irAInicioGuard, rolesGuard, soloInvitadosGuard } from './core/guards';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./pages/login/login').then((m) => m.LoginPage),
    canActivate: [soloInvitadosGuard], title: 'Iniciar sesión · ScribeTracker' },
  { path: 'recuperar', loadComponent: () => import('./pages/login/recuperar').then((m) => m.RecuperarPage),
    title: 'Recuperar contraseña · ScribeTracker' },
  { path: 'cambiar-password', loadComponent: () => import('./pages/login/cambiar-password').then((m) => m.CambiarPasswordPage),
    canActivate: [cambioPasswordGuard], title: 'Cambiar contraseña · ScribeTracker' },
  { path: 'promotor', canActivate: [rolesGuard('Promotor')],
    loadChildren: () => import('./promotor/promotor.routes').then((m) => m.RUTAS_PROMOTOR) },
  { path: 'panel', canActivate: [rolesGuard('Supervisor', 'Administrador')],
    loadChildren: () => import('./panel/panel.routes').then((m) => m.RUTAS_PANEL) },
  { path: '', pathMatch: 'full', canActivate: [irAInicioGuard], children: [] },
  { path: '**', canActivate: [irAInicioGuard], children: [] },
];
