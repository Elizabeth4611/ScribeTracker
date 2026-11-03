import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { erroresCampos, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { Tienda } from '../core/modelos';
import { MapaComponent, MarcadorMapa } from '../shared/mapa.component';

/** Gestión de tiendas (RF-19, RF-20, RF-21). */
@Component({
  selector: 'app-tiendas',
  imports: [FormsModule, MapaComponent],
  template: `
    <section class="tarjeta">
      <div class="barra-acciones">
        <h2>🏪 GESTIÓN DE TIENDAS</h2>
        <button type="button" class="boton boton--azul" (click)="nueva()">+ AGREGAR TIENDAS</button>
      </div>
      <div class="filtros">
        <input type="search" class="busqueda" placeholder="🔍 Buscar por nombre o cadena…" [(ngModel)]="q" (input)="pagina = 1; cargar()" />
        <select [(ngModel)]="cadena" (change)="pagina = 1; cargar()"><option value="">Todas las cadenas</option>@for (c of cadenas(); track c) { <option>{{ c }}</option> }</select>
        <select [(ngModel)]="zona" (change)="pagina = 1; cargar()"><option value="">Todas las zonas</option>@for (z of zonas(); track z) { <option>{{ z }}</option> }</select>
        <select [(ngModel)]="estatus" (change)="pagina = 1; cargar()"><option value="">Todas</option><option>Activa</option><option>Inactiva</option></select>
      </div>
      <table class="tabla">
        <thead><tr><th>Tienda</th><th>Cadena</th><th>Zona</th><th>Coordenadas</th><th>Radio</th><th>Estado</th><th></th></tr></thead>
        <tbody>
          @for (t of lista(); track t.id_tienda) {
            <tr>
              <td>{{ t.nombre_comercial }}, {{ t.sucursal }}<br /><small>{{ t.direccion_completa }}</small></td>
              <td>{{ t.cadena }}</td><td>{{ t.zona || '—' }}</td><td>{{ t.latitud.toFixed(5) }}, {{ t.longitud.toFixed(5) }}</td>
              <td>{{ t.radio_geocerca_m }} m</td><td>{{ t.estatus }}</td>
              <td class="fila-botones">
                <button type="button" class="boton boton--chico" (click)="editar(t)">Editar</button>
                <button type="button" class="boton boton--chico" (click)="estado(t)">{{ t.estatus === 'Activa' ? 'Desactivar' : 'Reactivar' }}</button>
              </td>
            </tr>
          } @empty { <tr><td colspan="7">No se encontraron tiendas.</td></tr> }
        </tbody>
      </table>
      <p class="paginacion">Mostrando {{ lista().length }} de {{ total() }}
        <button type="button" class="boton boton--chico" [disabled]="pagina === 1" (click)="pagina = pagina - 1; cargar()">←</button>
        página {{ pagina }}
        <button type="button" class="boton boton--chico" [disabled]="pagina * 10 >= total()" (click)="pagina = pagina + 1; cargar()">→</button></p>
    </section>

    @if (formAbierto()) {
      <section class="tarjeta formulario formulario--gris">
        <h2>🏪 {{ editId ? 'EDITAR TIENDA' : 'AGREGAR NUEVA TIENDA' }}</h2>
        @for (c of camposTexto; track c[0]) {
          <label>{{ c[1] }} <input [(ngModel)]="f[c[0]]" /></label>
          @if (campos()[c[0]]) { <small class="error-campo">{{ campos()[c[0]] }}</small> }
        }
        <p>Coordenadas GPS (haz clic en el mapa para tomarlas):</p>
        <div class="fila-2">
          <label>Latitud <input [(ngModel)]="f.latitud" inputmode="decimal" (change)="refrescar()" /></label>
          <label>Longitud <input [(ngModel)]="f.longitud" inputmode="decimal" (change)="refrescar()" /></label>
        </div>
        @if (campos()['latitud'] || campos()['longitud']) { <small class="error-campo">{{ campos()['latitud'] || campos()['longitud'] }}</small> }
        <app-mapa [marcadores]="marcadorForm()" alto="260px" [seleccionable]="true" (seleccion)="tomar($event)" />
        <div class="fila-2">
          <label>Radio de geocerca (m) <input type="number" [(ngModel)]="f.radio_geocerca_m" (change)="refrescar()" /></label>
          <label>Tiempo estimado (min) <input type="number" [(ngModel)]="f.tiempo_estimado_min" /></label>
        </div>
        @if (campos()['radio_geocerca_m']) { <small class="error-campo">{{ campos()['radio_geocerca_m'] }}</small> }
        <div class="fila-botones">
          <button type="button" class="boton boton--rojo" (click)="guardar()">GUARDAR</button>
          <button type="button" class="boton boton--rojo" (click)="formAbierto.set(false)">CANCELAR</button>
        </div>
      </section>
    }
  `,
})
export class TiendasPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly avisos = inject(AvisosService);
  readonly camposTexto: [string, string][] = [['nombre_comercial', 'Nombre comercial:'], ['cadena', 'Cadena:'],
    ['sucursal', 'Sucursal:'], ['direccion_completa', 'Dirección completa:'], ['zona', 'Zona:']];
  readonly lista = signal<Tienda[]>([]);
  readonly total = signal(0);
  readonly cadenas = signal<string[]>([]);
  readonly zonas = signal<string[]>([]);
  readonly formAbierto = signal(false);
  readonly campos = signal<Record<string, string>>({});
  private readonly version = signal(0);
  q = '';
  cadena = '';
  zona = '';
  estatus = '';
  pagina = 1;
  editId: number | null = null;
  f: any = {};
  private radioDefault = 50;

  readonly marcadorForm = computed<MarcadorMapa[]>(() => {
    this.version();
    const lat = Number(this.f.latitud);
    const lon = Number(this.f.longitud);
    if (!this.f.latitud || !this.f.longitud || isNaN(lat) || isNaN(lon)) return [];
    return [{ lat, lon, radio_m: Number(this.f.radio_geocerca_m) || this.radioDefault, color: '#E30613', tipo: 'tienda', etiqueta: '🏪', texto: this.f.nombre_comercial || 'Nueva tienda' }];
  });

  async ngOnInit() {
    await this.cargar();
    const o = await firstValueFrom(this.http.get<{ cadenas: string[]; zonas: string[]; radio_default: number }>('/api/tiendas/opciones'));
    this.cadenas.set(o.cadenas);
    this.zonas.set(o.zonas);
    this.radioDefault = o.radio_default;
  }

  async cargar() {
    const p = new URLSearchParams({ q: this.q, cadena: this.cadena, zona: this.zona, estatus: this.estatus, pagina: String(this.pagina) });
    const r = await firstValueFrom(this.http.get<{ tiendas: Tienda[]; total: number }>(`/api/tiendas?${p}`));
    this.lista.set(r.tiendas);
    this.total.set(r.total);
  }

  nueva() {
    this.editId = null;
    this.f = { nombre_comercial: '', cadena: '', sucursal: '', direccion_completa: '', zona: '', latitud: '', longitud: '', radio_geocerca_m: this.radioDefault, tiempo_estimado_min: null };
    this.campos.set({});
    this.formAbierto.set(true);
    this.refrescar();
  }

  editar(t: Tienda) {
    this.editId = t.id_tienda;
    this.f = { ...t };
    this.campos.set({});
    this.formAbierto.set(true);
    this.refrescar();
  }

  tomar(p: { lat: number; lon: number }) {
    this.f.latitud = p.lat.toFixed(7);
    this.f.longitud = p.lon.toFixed(7);
    this.refrescar();
  }

  refrescar() { this.version.update((v) => v + 1); }

  async guardar() {
    try {
      const r = await firstValueFrom(this.editId
        ? this.http.put<{ mensaje: string }>(`/api/tiendas/${this.editId}`, this.f)
        : this.http.post<{ mensaje: string }>('/api/tiendas', this.f));
      this.avisos.ok(r.mensaje);
      this.formAbierto.set(false);
      await this.cargar();
    } catch (e) {
      this.campos.set(erroresCampos(e));
      this.avisos.error(mensajeError(e));
    }
  }

  async estado(t: Tienda) {
    const accion = t.estatus === 'Activa' ? 'desactivar' : 'reactivar';
    if (accion === 'desactivar' && !confirm(`¿Desactivar ${t.nombre_comercial} ${t.sucursal}? Se conserva su historial.`)) return;
    try {
      const r = await firstValueFrom(this.http.post<{ mensaje: string }>(`/api/tiendas/${t.id_tienda}/${accion}`, {}));
      this.avisos.ok(r.mensaje);
      await this.cargar();
    } catch (e) { this.avisos.error(mensajeError(e)); }
  }
}
