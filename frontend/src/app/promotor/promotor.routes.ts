import { Routes } from '@angular/router';

import { PromotorShell } from './promotor-shell';

export const RUTAS_PROMOTOR: Routes = [
  {
    path: '', component: PromotorShell, children: [
      { path: '', loadComponent: () => import('./inicio').then((m) => m.InicioPromotor), title: 'Inicio · ScribeTracker', data: { titulo: 'Inicio' } },
      { path: 'jornada', loadComponent: () => import('./jornada').then((m) => m.JornadaPage), title: 'Entrada/salida · ScribeTracker', data: { titulo: 'Entrada/salida' } },
      { path: 'visita', loadComponent: () => import('./visita').then((m) => m.VisitaPage), title: 'Evidencias · ScribeTracker', data: { titulo: 'Evidencias' } },
      { path: 'historial', loadComponent: () => import('./historial').then((m) => m.HistorialPage), title: 'Historial · ScribeTracker', data: { titulo: 'Historial' } },
      { path: 'pausas', loadComponent: () => import('./pausas').then((m) => m.PausasPage), title: 'Pausas · ScribeTracker', data: { titulo: 'Pausas' } },
      { path: 'configuracion', loadComponent: () => import('./configuracion').then((m) => m.ConfiguracionPromotor), title: 'Configuración · ScribeTracker', data: { titulo: 'Configuración' } },
    ],
  },
];
