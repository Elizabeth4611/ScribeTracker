import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { erroresCampos, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Usuario } from '../core/modelos';

interface Acceso { envio_correo: string; password_temporal?: string; aviso?: string }

/** Gestión de usuarios (ERS 3.6: RF-03 a RF-07). */
@Component({
  selector: 'app-usuarios',
  imports: [FormsModule],
  template: `
    <section class="tarjeta">
      <div class="barra-acciones">
        <h2>👥 GESTIÓN DE USUARIOS</h2>
        <button type="button" class="boton boton--azul" (click)="nuevo()">+ AGREGAR USUARIO</button>
      </div>
      <div class="filtros">
        <input type="search" class="busqueda" placeholder="🔍 Buscar por nombre o número de empleado…" [(ngModel)]="q" (input)="pagina = 1; cargar()" />
        <select [(ngModel)]="rol" (change)="pagina = 1; cargar()"><option value="">Todos los roles</option><option>Promotor</option><option>Supervisor</option><option>Administrador</option></select>
        <select [(ngModel)]="estatus" (change)="pagina = 1; cargar()"><option value="">Todos</option><option>Activo</option><option>Inactivo</option></select>
      </div>
      <table class="tabla">
        <thead><tr><th>Nombre</th><th>ID</th><th>Rol</th><th>Supervisor</th><th>Teléfono</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          @for (u of lista(); track u.id_usuario) {
            <tr>
              <td>{{ u.nombre_completo }}<br /><small>{{ u.correo_electronico }}</small></td>
              <td>{{ u.numero_empleado || '—' }}</td><td>{{ u.rol }}</td><td>{{ u.nombre_supervisor || '—' }}</td>
              <td>{{ u.telefono || '—' }}</td><td>{{ u.estatus }}</td>
              <td class="fila-botones">
                <button type="button" class="boton boton--chico" (click)="editar(u)">Editar</button>
                <button type="button" class="boton boton--chico" (click)="cambiarEstatus(u)">{{ u.estatus === 'Activo' ? 'Desactivar' : 'Reactivar' }}</button>
                <button type="button" class="boton boton--chico" (click)="restablecer(u)">Contraseña</button>
              </td>
            </tr>
          } @empty { <tr><td colspan="7">Sin resultados.</td></tr> }
        </tbody>
      </table>
      <p class="paginacion">Mostrando {{ lista().length }} de {{ total() }}
        <button type="button" class="boton boton--chico" [disabled]="pagina === 1" (click)="pagina = pagina - 1; cargar()">←</button>
        página {{ pagina }}
        <button type="button" class="boton boton--chico" [disabled]="pagina * 10 >= total()" (click)="pagina = pagina + 1; cargar()">→</button></p>
    </section>

    @if (acceso(); as a) {
      <section class="tarjeta destacado">
        <h2>Acceso del usuario</h2>
        @if (a.password_temporal) {
          <p>{{ a.aviso }}</p>
          <p class="clave">Contraseña temporal: <b>{{ a.password_temporal }}</b></p>
          <p class="nota">Envío por correo: {{ a.envio_correo === 'no_configurado' ? 'no configurado (falta SMTP en .env)' : 'falló' }}. La cuenta ya quedó creada; si se pierde esta contraseña, genera otra con "Contraseña".</p>
        } @else { <p>Las credenciales se enviaron por correo.</p> }
        <button type="button" class="boton" (click)="acceso.set(null)">ENTENDIDO</button>
      </section>
    }

    @if (formAbierto()) {
      <section class="tarjeta formulario formulario--gris">
        <h2>👥 {{ editId ? 'EDITAR USUARIO' : 'AGREGAR NUEVO USUARIO' }}</h2>
        <label>Nombre completo: <input [(ngModel)]="f.nombre_completo" /></label>
        @if (campos()['nombre_completo']) { <small class="error-campo">{{ campos()['nombre_completo'] }}</small> }
        <label>Número de empleado: <input [(ngModel)]="f.numero_empleado" /></label>
        @if (campos()['numero_empleado']) { <small class="error-campo">{{ campos()['numero_empleado'] }}</small> }
        <label>Teléfono: <input [(ngModel)]="f.telefono" inputmode="tel" /></label>
        @if (campos()['telefono']) { <small class="error-campo">{{ campos()['telefono'] }}</small> }
        <label>Correo electrónico: <input type="email" [(ngModel)]="f.correo_electronico" /></label>
        @if (campos()['correo_electronico']) { <small class="error-campo">{{ campos()['correo_electronico'] }}</small> }
        <label>Rol: <select [(ngModel)]="f.rol"><option>Promotor</option><option>Supervisor</option><option>Administrador</option></select></label>
        @if (f.rol === 'Promotor') {
          <label>Supervisor: <select [(ngModel)]="f.id_supervisor">
            <option [ngValue]="null">Selecciona…</option>
            @for (s of supervisores(); track s.id_usuario) { <option [ngValue]="s.id_usuario">{{ s.nombre_completo }}</option> }
          </select></label>
          @if (campos()['id_supervisor']) { <small class="error-campo">{{ campos()['id_supervisor'] }}</small> }
          <label>Tipo: <select [(ngModel)]="f.tipo_contrato"><option [ngValue]="null">—</option><option>Planta</option><option>Temporada</option></select></label>
        }
        <div class="fila-botones">
          <button type="button" class="boton boton--rojo" (click)="guardar()">GUARDAR</button>
          <button type="button" class="boton boton--rojo" (click)="formAbierto.set(false)">CANCELAR</button>
        </div>
      </section>
    }
  `,
})
export class UsuariosPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly lista = signal<Usuario[]>([]);
  readonly total = signal(0);
  readonly supervisores = signal<{ id_usuario: number; nombre_completo: string }[]>([]);
  readonly formAbierto = signal(false);
  readonly campos = signal<Record<string, string>>({});
  readonly acceso = signal<Acceso | null>(null);
  q = '';
  rol = '';
  estatus = '';
  pagina = 1;
  editId: number | null = null;
  f: any = {};

  ngOnInit() { void this.cargar(); }

  async cargar() {
    const p = new URLSearchParams({ q: this.q, rol: this.rol, estatus: this.estatus, pagina: String(this.pagina), por_pagina: '10' });
    const r = await firstValueFrom(this.http.get<{ usuarios: Usuario[]; total: number }>(`/api/usuarios?${p}`));
    this.lista.set(r.usuarios);
    this.total.set(r.total);
  }

  private async cargarSupervisores() {
    this.supervisores.set((await firstValueFrom(this.http.get<{ supervisores: any[] }>('/api/usuarios/supervisores'))).supervisores);
  }

  async nuevo() {
    await this.cargarSupervisores();
    this.editId = null;
    this.f = { nombre_completo: '', numero_empleado: '', telefono: '', correo_electronico: '', rol: 'Promotor', id_supervisor: null, tipo_contrato: null };
    this.campos.set({});
    this.formAbierto.set(true);
  }

  async editar(u: Usuario) {
    await this.cargarSupervisores();
    this.editId = u.id_usuario;
    this.f = { ...u };
    this.campos.set({});
    this.formAbierto.set(true);
  }

  async guardar() {
    try {
      if (this.editId) {
        const r = await firstValueFrom(this.http.put<{ mensaje: string; aviso: string | null }>(`/api/usuarios/${this.editId}`, this.f));
        this.avisos.ok(r.mensaje);
        if (r.aviso) this.avisos.info(r.aviso);
      } else {
        const r = await firstValueFrom(this.http.post<{ mensaje: string; acceso: Acceso }>('/api/usuarios', this.f));
        this.avisos.ok(r.mensaje);
        this.acceso.set(r.acceso);
      }
      this.formAbierto.set(false);
      await this.cargar();
    } catch (e) {
      this.campos.set(erroresCampos(e));
      this.avisos.error(mensajeError(e));
    }
  }

  async cambiarEstatus(u: Usuario) {
    const accion = u.estatus === 'Activo' ? 'desactivar' : 'reactivar';
    if (accion === 'desactivar' && !confirm(`¿Desactivar a ${u.nombre_completo}? Perderá el acceso y se liberarán sus tiendas futuras. El registro se conserva.`)) return;
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string }>(`/api/usuarios/${u.id_usuario}/${accion}`, {}));
      this.avisos.ok(r.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async restablecer(u: Usuario) {
    if (!confirm(`¿Generar una contraseña temporal nueva para ${u.nombre_completo}?`)) return;
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string; acceso: Acceso }>(`/api/usuarios/${u.id_usuario}/restablecer-password`, {}));
      this.avisos.ok(r.mensaje);
      this.acceso.set(r.acceso);
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
