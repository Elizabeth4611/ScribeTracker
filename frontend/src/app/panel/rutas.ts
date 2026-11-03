import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { erroresCampos, hoyIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Ruta, Tienda } from '../core/modelos';
import { BuscadorTiendas } from './buscador-tiendas';
import { SelectorPromotor } from './selector-promotor';

const DIAS = ['LUN', 'MAR', 'MIE', 'JUE', 'VIE', 'SAB', 'DOM'];

/** Gestión de rutas (prototipo admin: nombre, promotor, días programados, tiendas). */
@Component({
  selector: 'app-rutas',
  imports: [FormsModule, SelectorPromotor, BuscadorTiendas],
  template: `
    <section class="tarjeta">
      <div class="barra-acciones">
        <h2>🗺️ GESTIÓN DE RUTAS</h2>
        <button type="button" class="boton boton--azul" (click)="nueva()">+ CREAR RUTA</button>
      </div>
      <input type="search" class="busqueda" placeholder="🔍 Buscar por nombre de ruta, promotor o número de empleado…" [(ngModel)]="q" (input)="cargar()" />
      <table class="tabla">
        <thead><tr><th>Ruta</th><th>Promotor</th><th>Días</th><th>Tiendas</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          @for (r of rutas(); track r.id_ruta) {
            <tr>
              <td>{{ r.nombre_ruta }}</td><td>{{ r.nombre_promotor }}</td><td>{{ r.dias_programados.join('-') }}</td>
              <td>{{ r.tiendas.length }}</td><td>{{ r.estado }}</td>
              <td class="fila-botones">
                <button type="button" class="boton boton--chico" (click)="editar(r)">Editar</button>
                <button type="button" class="boton boton--chico" (click)="estado(r)">{{ r.estado === 'Activa' ? 'Desactivar' : 'Reactivar' }}</button>
                @if (r.estado === 'Activa') { <button type="button" class="boton boton--chico" (click)="aplicando.set(r)">Aplicar a fechas</button> }
              </td>
            </tr>
          } @empty { <tr><td colspan="6">No hay rutas.</td></tr> }
        </tbody>
      </table>
    </section>

    @if (aplicando(); as r) {
      <section class="tarjeta formulario">
        <h2>Aplicar "{{ r.nombre_ruta }}" ({{ r.dias_programados.join('-') }})</h2>
        <p class="nota">Crea asignaciones por fecha en los días programados. Los días que ya tienen tiendas se omiten.</p>
        <label>Desde <input type="date" [(ngModel)]="desde" [min]="hoy" /></label>
        <label>Hasta <input type="date" [(ngModel)]="hasta" [min]="desde" /></label>
        <div class="fila-botones">
          <button type="button" class="boton boton--rojo" (click)="aplicar(r)">APLICAR</button>
          <button type="button" class="boton" (click)="aplicando.set(null)">CANCELAR</button>
        </div>
      </section>
    }

    @if (editando()) {
      <section class="tarjeta formulario">
        <h2>🏪 {{ form.id_ruta ? 'EDITAR RUTA' : 'CREAR UNA RUTA' }}</h2>
        <label>Nombre de la ruta: <input [(ngModel)]="form.nombre_ruta" /></label>
        @if (campos()['nombre_ruta']) { <small class="error-campo">{{ campos()['nombre_ruta'] }}</small> }
        <label>Promotor asignado: <app-selector-promotor [(valor)]="idPromotor" /></label>
        <fieldset><legend>Días programados:</legend>
          @for (d of dias; track d) { <label class="check"><input type="checkbox" [checked]="form.dias.includes(d)" (change)="alternar(d)" /> {{ d }}</label> }
        </fieldset>
        @if (campos()['dias_programados']) { <small class="error-campo">{{ campos()['dias_programados'] }}</small> }
        <p>Tiendas asignadas (en orden de visita):</p>
        <ol class="lista-orden">
          @for (t of form.tiendas; track t.id_tienda; let i = $index) {
            <li><span>{{ t.nombre_comercial }} {{ t.sucursal }}</span><button type="button" class="boton boton--chico" (click)="form.tiendas.splice(i, 1)">✕</button></li>
          }
        </ol>
        <app-buscador-tiendas (elegida)="agregar($event)" />
        @if (campos()['tiendas']) { <small class="error-campo">{{ campos()['tiendas'] }}</small> }
        <div class="fila-botones">
          <button type="button" class="boton boton--rojo" (click)="guardar()">GUARDAR</button>
          <button type="button" class="boton" (click)="editando.set(false)">CANCELAR</button>
        </div>
      </section>
    }
  `,
})
export class RutasPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly dias = DIAS;
  readonly hoy = hoyIso();
  readonly rutas = signal<Ruta[]>([]);
  readonly editando = signal(false);
  readonly aplicando = signal<Ruta | null>(null);
  readonly campos = signal<Record<string, string>>({});
  readonly idPromotor = signal<number | null>(null);
  q = '';
  desde = hoyIso();
  hasta = hoyIso();
  form: { id_ruta: number | null; nombre_ruta: string; dias: string[]; tiendas: Tienda[] } = { id_ruta: null, nombre_ruta: '', dias: [], tiendas: [] };

  ngOnInit() { void this.cargar(); }

  async cargar() {
    const r = await firstValueFrom(this.http.get<{ rutas: Ruta[] }>(`/api/rutas?q=${encodeURIComponent(this.q)}`));
    this.rutas.set(r.rutas);
  }

  nueva() {
    this.form = { id_ruta: null, nombre_ruta: '', dias: [], tiendas: [] };
    this.idPromotor.set(null);
    this.campos.set({});
    this.editando.set(true);
  }

  editar(r: Ruta) {
    this.form = { id_ruta: r.id_ruta, nombre_ruta: r.nombre_ruta, dias: [...r.dias_programados], tiendas: r.tiendas.map((t) => t as Tienda) };
    this.idPromotor.set(r.id_promotor);
    this.campos.set({});
    this.editando.set(true);
  }

  alternar(d: string) {
    this.form.dias = this.form.dias.includes(d) ? this.form.dias.filter((x) => x !== d) : [...this.form.dias, d];
  }

  agregar(t: Tienda) {
    if (!this.form.tiendas.some((x) => x.id_tienda === t.id_tienda)) this.form.tiendas.push(t);
  }

  async guardar() {
    const cuerpo = { nombre_ruta: this.form.nombre_ruta, id_promotor: this.idPromotor(), dias_programados: this.form.dias,
      tiendas: this.form.tiendas.map((t) => t.id_tienda) };
    try {
      const r = await firstValueFrom(this.form.id_ruta
        ? this.http.put<{ mensaje: string; advertencias: string[] }>(`/api/rutas/${this.form.id_ruta}`, cuerpo)
        : this.http.post<{ mensaje: string; advertencias: string[] }>('/api/rutas', cuerpo));
      this.avisos.ok(r.mensaje);
      r.advertencias?.forEach((a) => this.avisos.alerta(a));
      this.editando.set(false);
      await this.cargar();
    } catch (e) {
      this.campos.set(erroresCampos(e));
      this.avisos.error(mensajeError(e));
    }
  }

  async estado(r: Ruta) {
    try {
      const x = await firstValueFrom(this.http.post<{ mensaje: string }>(`/api/rutas/${r.id_ruta}/${r.estado === 'Activa' ? 'desactivar' : 'reactivar'}`, {}));
      this.avisos.ok(x.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }

  async aplicar(r: Ruta) {
    try {
      const x = await firstValueFrom(this.http.post<{ mensaje: string }>(`/api/rutas/${r.id_ruta}/aplicar`, { desde: this.desde, hasta: this.hasta }));
      this.avisos.ok(x.mensaje);
      this.aplicando.set(null);
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
