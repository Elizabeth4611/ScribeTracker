import { Routes } from '@angular/router';

import { rolesGuard } from '../core/guards';
import { PanelShell } from './panel-shell';

const soloAdmin = [rolesGuard('Administrador')];

export const RUTAS_PANEL: Routes = [
  {
    path: '', component: PanelShell, children: [
      { path: 'inicio', canActivate: soloAdmin, loadComponent: () => import('./admin-inicio').then((m) => m.AdminInicio), title: 'Resumen · ScribeTracker', data: { titulo: 'Resumen general' } },
      { path: 'supervision', loadComponent: () => import('./mapa-supervision').then((m) => m.MapaSupervision), title: 'Monitoreo · ScribeTracker', data: { titulo: 'Monitoreo en tiempo real' } },
      { path: 'seguimiento', loadComponent: () => import('./seguimiento').then((m) => m.Seguimiento), title: 'Seguimiento · ScribeTracker', data: { titulo: 'Rutas y seguimiento' } },
      { path: 'asignacion', loadComponent: () => import('./asignacion').then((m) => m.Asignacion), title: 'Gestión de rutas · ScribeTracker', data: { titulo: 'Gestión de rutas' } },
      { path: 'rutas', loadComponent: () => import('./rutas').then((m) => m.RutasPage), title: 'Rutas · ScribeTracker', data: { titulo: 'Rutas' } },
      { path: 'incidencias', loadComponent: () => import('./incidencias').then((m) => m.IncidenciasPage), title: 'Incidencias · ScribeTracker', data: { titulo: 'Incidencias' } },
      { path: 'reportes', loadComponent: () => import('./reportes').then((m) => m.ReportesPage), title: 'Reportes · ScribeTracker', data: { titulo: 'Reportes' } },
      { path: 'usuarios', canActivate: soloAdmin, loadComponent: () => import('./usuarios').then((m) => m.UsuariosPage), title: 'Usuarios · ScribeTracker', data: { titulo: 'Gestión de usuarios' } },
      { path: 'tiendas', canActivate: soloAdmin, loadComponent: () => import('./tiendas').then((m) => m.TiendasPage), title: 'Tiendas · ScribeTracker', data: { titulo: 'Tiendas' } },
      { path: 'parametros', canActivate: soloAdmin, loadComponent: () => import('./parametros').then((m) => m.ParametrosPage), title: 'Parámetros · ScribeTracker', data: { titulo: 'Parámetros globales' } },
      { path: 'configuracion', loadComponent: () => import('./configuracion').then((m) => m.ConfiguracionPanel), title: 'Configuración · ScribeTracker', data: { titulo: 'Configuración' } },
      { path: '', pathMatch: 'full', redirectTo: 'supervision' },
    ],
  },
];
