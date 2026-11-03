import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { hora } from '../core/api';
import { CATEGORIAS, Categoria, Evidencia } from '../core/modelos';
import { CamaraComponent } from '../shared/camara.component';
import { PromotorService } from './promotor.service';

/**
 * Captura de evidencias (RF-05, RF-06) y check-out (RF-04). Cada visita
 * necesita al menos una foto válida de las cuatro categorías; si no hay
 * promociones se fotografía el área de exhibición Scribe en esa categoría.
 */
@Component({
  selector: 'app-visita',
  imports: [CamaraComponent, FormsModule, RouterLink, DecimalPipe],
  template: `
    @let v = ps.visitaEnCurso();
    @if (!v) {
      <p class="nota">No tienes una visita abierta. Haz check-in en una tienda desde Entrada/salida.</p>
      <a routerLink="/promotor/jornada" class="boton boton--rojo">IR A ENTRADA/SALIDA</a>
    } @else {
      <p class="tienda-actual">Tienda: <b>{{ v.tienda }}</b></p>
      @if (v.pendiente) { <p class="etiqueta etiqueta--pendiente">Check-in pendiente de sincronizar</p> }
      <app-camara (capturada)="foto.set($event)" />
      <label class="campo"><span>Selecciona una categoría:</span>
        <select [(ngModel)]="categoria">
          @for (c of categorias; track c) { <option [value]="c">{{ c }}</option> }
        </select>
      </label>
      @if (categoria === 'Promociones') {
        <label class="check"><input type="checkbox" [(ngModel)]="sinPromocion" /> No hay promociones: fotografío el área de exhibición Scribe</label>
      }
      <div class="fila-botones">
        @if (!foto()) {
          <button type="button" class="boton" (click)="tomar()">📷 CAPTURAR</button>
        } @else {
          <button type="button" class="boton" (click)="repetir()">REPETIR</button>
          <button type="button" class="boton boton--rojo" (click)="enviar()" [disabled]="ps.ocupado()">ENVIAR</button>
        }
      </div>

      <h2 class="subtitulo">Categorías obligatorias</h2>
      <ul class="checklist">
        @for (c of categorias; track c) {
          <li [class.ok]="v.validas.includes(c)" [class.pend]="!v.validas.includes(c) && v.pendientes.includes(c)">
            {{ v.validas.includes(c) ? '✔' : v.pendientes.includes(c) ? '⏳' : '✖' }} {{ c }}
            <small>{{ v.validas.includes(c) ? 'válida' : v.pendientes.includes(c) ? 'por sincronizar (sin validar)' : 'falta' }}</small>
          </li>
        }
      </ul>

      @if (evidencias().length) {
        <h2 class="subtitulo">Fotos enviadas</h2>
        <div class="galeria">
          @for (e of evidencias(); track e.id_evidencia) {
            <figure [class.mala]="e.estatus_validacion !== 'Válida'">
              <img [src]="e.url" [alt]="e.categoria" loading="lazy" />
              <figcaption>{{ e.categoria }} · {{ hora(e.fecha_hora_captura) }}<br />{{ e.estatus_validacion }} ({{ e.distancia_m | number: '1.0-0' }} m)</figcaption>
            </figure>
          }
        </div>
      }

      <button type="button" class="boton boton--rojo boton--grande" (click)="salir()" [disabled]="ps.ocupado()">CHECK-OUT</button>
      @if (ps.faltantes(v).length) { <p class="nota">Faltan: {{ ps.faltantes(v).join(', ') }}. El servidor no permitirá el check-out sin las 4 categorías válidas.</p> }
    }
  `,
})
export class VisitaPage {
  readonly ps = inject(PromotorService);
  private readonly router = inject(Router);
  private readonly camara = viewChild(CamaraComponent);
  readonly categorias = CATEGORIAS;
  readonly hora = hora;
  readonly foto = signal<{ foto: Blob; ancho: number; alto: number } | null>(null);
  categoria: Categoria = 'Anaquel antes';
  sinPromocion = false;

  readonly evidencias = computed<Evidencia[]>(() => {
    const v = this.ps.visitaEnCurso();
    const a = this.ps.hoy()?.asignaciones.find((x) => x.id_asignacion === v?.id_asignacion);
    return a?.visita?.evidencias ?? [];
  });

  async tomar() {
    await this.camara()?.capturar();
  }

  repetir() {
    this.foto.set(null);
    this.camara()?.repetir();
  }

  async enviar() {
    const v = this.ps.visitaEnCurso();
    const f = this.foto();
    if (!v || !f) return;
    const r = await this.ps.subirFoto(v, this.categoria, f.foto, { ancho: f.ancho, alto: f.alto },
      this.categoria === 'Promociones' && this.sinPromocion);
    if (r) {
      this.repetir();
      const sig = CATEGORIAS.find((c) => !this.ps.visitaEnCurso()?.validas.includes(c) && !this.ps.visitaEnCurso()?.pendientes.includes(c));
      if (sig) this.categoria = sig;
    }
  }

  async salir() {
    const v = this.ps.visitaEnCurso();
    if (!v) return;
    const r = await this.ps.checkout(v);
    if (r && r.estado !== 'rechazado') void this.router.navigateByUrl('/promotor/jornada');
  }
}
