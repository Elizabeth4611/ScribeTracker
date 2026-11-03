import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../core/auth.service';

@Component({
  selector: 'app-configuracion-panel',
  imports: [RouterLink],
  template: `
    @if (vista() === 'menu') {
      <div class="menu-rojo">
        <button type="button" (click)="vista.set('perfil')">MI PERFIL 👤</button>
        <button type="button" (click)="vista.set('ayuda')">AYUDA ⁉</button>
        <a routerLink="/cambiar-password">CAMBIAR CONTRASEÑA 🔑</a>
      </div>
      <button type="button" class="boton boton--azul" (click)="auth.cerrarSesion()">CERRAR SESIÓN</button>
    } @else if (vista() === 'perfil') {
      @let u = auth.usuario();
      <div class="perfil perfil--panel">
        <div class="avatar">👤</div>
        <label>NOMBRE COMPLETO:</label><p class="caja-roja">{{ u?.nombre_completo }}</p>
        <label>CORREO:</label><p class="caja-roja">{{ u?.correo_electronico }}</p>
        <label>ACTIVO DESDE:</label><p class="caja-roja">{{ u?.fecha_alta?.slice(0, 10) || '—' }}</p>
        <label>ROL:</label><p class="caja-roja">{{ u?.rol?.toUpperCase() }}</p>
      </div>
      <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
    } @else {
      <div class="menu-rojo menu-rojo--texto">
        <p>¿Cómo creo un nuevo usuario? Ve a Usuarios y presiona "+ Agregar usuario".</p>
        <p>¿Cómo agrego una tienda? Ve a Tiendas, presiona "+ Agregar tiendas" y toma las coordenadas en el mapa.</p>
        <p>¿Cómo asigno tiendas? En Gestión de rutas elige promotor y fecha, agrega las tiendas en orden y guarda.</p>
        <p>¿Cómo genero un reporte? Ve a Reportes, selecciona fecha, tipo y contenido, y descarga el PDF.</p>
        <p>CONTÁCTANOS: +52 (55) 9126-6001 · contacto&#64;biopappel.com</p>
      </div>
      <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
    }
  `,
})
export class ConfiguracionPanel {
  readonly auth = inject(AuthService);
  readonly vista = signal<'menu' | 'perfil' | 'ayuda'>('menu');
}
