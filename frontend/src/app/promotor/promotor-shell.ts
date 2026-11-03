import { Location } from '@angular/common';
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../core/auth.service';
import { PromotorService } from './promotor.service';

/** Marco de la vista móvil del promotor (prototipo: encabezado y barra inferior). */
@Component({
  selector: 'app-promotor-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="movil">
      <header class="movil__cabecera">
        <span class="logo">Scribe</span>
        <div class="movil__titulos">
          <strong>ScribeTracker: {{ titulo() }}</strong>
          <small>Promotor: {{ auth.usuario()?.nombre_completo }}</small>
        </div>
        <button type="button" class="icono-salir" title="Cerrar sesión" (click)="salir()">⎋</button>
      </header>
      @if (!ps.cola.enLinea() || ps.cola.pendientes().length || ps.desdeCache()) {
        <div class="franja" [class.franja--alerta]="!ps.cola.enLinea()">
          @if (!ps.cola.enLinea()) { Sin conexión · }
          {{ ps.cola.pendientes().length }} pendiente(s) de sincronizar
          @if (ps.desdeCache()) { · datos guardados en el teléfono }
        </div>
      }
      <main class="movil__contenido"><router-outlet /></main>
      <nav class="movil__barra" aria-label="Navegación">
        <button type="button" (click)="atras()" title="Atrás">←</button>
        <a routerLink="/promotor" [routerLinkActiveOptions]="{ exact: true }" routerLinkActive="activo" title="Inicio">⌂</a>
        <a routerLink="/promotor/historial" routerLinkActive="activo" title="Historial">✔</a>
        <a routerLink="/promotor/pausas" routerLinkActive="activo" title="Pausas">⏸</a>
        <a routerLink="/promotor/configuracion" routerLinkActive="activo" title="Configuración">⚙</a>
      </nav>
    </div>
  `,
})
export class PromotorShell implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  readonly ps = inject(PromotorService);
  private readonly router = inject(Router);
  private readonly ruta = inject(ActivatedRoute);
  private readonly location = inject(Location);
  readonly titulo = signal('Inicio');
  private refresco?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.leerTitulo();
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => this.leerTitulo());
    void this.ps.cargar();
    this.refresco = setInterval(() => void this.ps.cargar(), 60_000);
  }

  ngOnDestroy() { clearInterval(this.refresco); }

  atras() { this.location.back(); }

  async salir() {
    const n = this.ps.cola.pendientes().length;
    if (n && !confirm(`Tienes ${n} registro(s) sin sincronizar. Si cierras sesión se enviarán cuando vuelvas a entrar. ¿Cerrar sesión?`)) return;
    await this.auth.cerrarSesion();
  }

  private leerTitulo() {
    let r = this.ruta.snapshot;
    while (r.firstChild) r = r.firstChild;
    this.titulo.set(r.data['titulo'] ?? 'Inicio');
  }
}
