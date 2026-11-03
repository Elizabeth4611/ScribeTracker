import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../core/auth.service';

/** Marco del panel web. Supervisor: tema oscuro; Administrador: tema claro (prototipos). */
@Component({
  selector: 'app-panel-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="panel" [class.panel--oscuro]="esSupervisor()">
      <header class="panel__cabecera">
        <span class="logo">Scribe</span>
        <div class="panel__titulos">
          <strong>ScribeTracker: {{ titulo() }}</strong>
          <small>👤 {{ auth.usuario()?.rol }}: {{ auth.usuario()?.nombre_completo }}</small>
        </div>
        <button type="button" class="icono-salir" title="Cerrar sesión" (click)="auth.cerrarSesion()">⎋</button>
      </header>
      <nav class="panel__menu">
        @if (!esSupervisor()) { <a routerLink="inicio" routerLinkActive="activo">Inicio</a> }
        <a routerLink="supervision" routerLinkActive="activo">{{ esSupervisor() ? 'Módulo de supervisión' : 'Monitoreo' }}</a>
        <a routerLink="seguimiento" routerLinkActive="activo">Rutas del día</a>
        <a routerLink="asignacion" routerLinkActive="activo">Gestión de rutas</a>
        <a routerLink="rutas" routerLinkActive="activo">Rutas (plantillas)</a>
        <a routerLink="incidencias" routerLinkActive="activo">Incidencias</a>
        <a routerLink="reportes" routerLinkActive="activo">Reportes</a>
        @if (!esSupervisor()) {
          <a routerLink="usuarios" routerLinkActive="activo">Usuarios</a>
          <a routerLink="tiendas" routerLinkActive="activo">Tiendas</a>
          <a routerLink="parametros" routerLinkActive="activo">Parámetros</a>
        }
        <a routerLink="configuracion" routerLinkActive="activo">Configuración</a>
      </nav>
      <main class="panel__contenido"><router-outlet /></main>
    </div>
  `,
})
export class PanelShell implements OnInit {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  readonly titulo = signal('');
  readonly esSupervisor = computed(() => this.auth.usuario()?.rol === 'Supervisor');

  ngOnInit() {
    this.leer();
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => this.leer());
  }

  private leer() {
    let r = this.ruta.snapshot;
    while (r.firstChild) r = r.firstChild;
    this.titulo.set(r.data['titulo'] ?? '');
  }
}
