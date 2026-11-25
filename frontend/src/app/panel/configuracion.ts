import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { PushService } from '../core/push.service';

@Component({
  selector: 'app-configuracion-panel',
  imports: [RouterLink],
  template: `
    @if (vista() === 'menu') {
      <div class="menu-rojo">
        <button type="button" (click)="vista.set('perfil')">MI PERFIL</button>
        <button type="button" (click)="vista.set('ayuda')">AYUDA</button>
        <a routerLink="/cambiar-password">CAMBIAR CONTRASEÑA</a>
        <button type="button" (click)="abrirNotificaciones()">NOTIFICACIONES</button>
      </div>
      <button type="button" class="boton boton--azul" (click)="auth.cerrarSesion()">CERRAR SESIÓN</button>
    } @else if (vista() === 'perfil') {
      @let u = auth.usuario();
      <div class="perfil perfil--panel">
        <div class="avatar" style="color: #fff; font-weight: 700; font-size: 2.2rem">{{ iniciales(u?.nombre_completo) }}</div>
        <label>NOMBRE COMPLETO:</label><p class="caja-roja">{{ u?.nombre_completo }}</p>
        <label>CORREO:</label><p class="caja-roja">{{ u?.correo_electronico }}</p>
        <label>ACTIVO DESDE:</label><p class="caja-roja">{{ u?.fecha_alta?.slice(0, 10) || '—' }}</p>
        <label>ROL:</label><p class="caja-roja">{{ u?.rol?.toUpperCase() }}</p>
      </div>
      <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
    } @else if (vista() === 'notificaciones') {
      <div class="menu-rojo menu-rojo--texto">
        <p><b>Notificaciones push de alertas críticas</b></p>
        <p>Te llegan aunque no tengas el panel abierto: sin llegada a la primera tienda, inactividad, sin ubicación reciente y fotos fuera de geocerca o repetidas.</p>
        <p>Estado en este navegador: <b>{{ textoEstado() }}</b></p>
      </div>
      <div class="fila-botones">
        @if (push.estado() === 'activo') {
          <button type="button" class="boton boton--rojo" (click)="probar()">PROBAR NOTIFICACIÓN</button>
          <button type="button" class="boton" (click)="desactivar()">DESACTIVAR</button>
        } @else if (push.estado() === 'inactivo') {
          <button type="button" class="boton boton--rojo" (click)="activar()">ACTIVAR NOTIFICACIONES</button>
        }
        <button type="button" class="boton" (click)="vista.set('menu')">← VOLVER</button>
      </div>
    } @else {
      <div class="menu-rojo menu-rojo--texto">
        <p><b>Manual de usuario</b><br />Explica paso a paso cada pantalla del {{ esAdmin() ? 'administrador' : 'supervisor' }}.</p>
      </div>
      <div class="fila-botones">
        <a class="boton boton--rojo" [href]="'/ayuda/manual_de_usuario.pdf#page=' + (esAdmin() ? 20 : 11)" target="_blank" rel="noopener">VER MANUAL DE USUARIO</a>
        <a class="boton" href="/ayuda/manual_de_usuario.pdf" download="Manual de usuario ScribeTracker.pdf">DESCARGAR MANUAL (PDF)</a>
      </div>
      <div class="menu-rojo menu-rojo--texto">
        <p><b>Preguntas frecuentes</b></p>
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
  readonly push = inject(PushService);
  private readonly avisos = inject(AvisosService);

  async abrirNotificaciones() { this.vista.set('notificaciones'); await this.push.revisar(); }

  textoEstado(): string {
    return { 'activo': 'Activadas', 'inactivo': 'Desactivadas', 'bloqueado': 'Bloqueadas en el navegador (permítelas en la configuración del sitio)',
      'no-soportado': 'No disponibles: se necesita HTTPS o localhost y un navegador compatible' }[this.push.estado()];
  }

  async activar() { try { this.avisos.ok(await this.push.activar()); } catch (e) { this.avisos.error(mensajeError(e)); } }
  async desactivar() { try { this.avisos.ok(await this.push.desactivar()); } catch (e) { this.avisos.error(mensajeError(e)); } }
  async probar() { try { this.avisos.ok(await this.push.probar()); } catch (e) { this.avisos.error(mensajeError(e)); } }
  readonly vista = signal<'menu' | 'perfil' | 'ayuda' | 'notificaciones'>('menu');

  /** El manual abre en la sección del rol (supervisor: pág. 11 · administrador: pág. 20 del PDF). */
  esAdmin(): boolean { return this.auth.usuario()?.rol === 'Administrador'; }

  /** Iniciales del nombre para el círculo del perfil (en lugar de un emoji). */
  iniciales(nombre?: string | null): string {
    return (nombre ?? '').trim().split(/\s+/).slice(0, 2).map((p) => p[0] ?? '').join('').toUpperCase();
  }
}
