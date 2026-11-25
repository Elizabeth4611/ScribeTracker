import { Component, computed, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { duracion, hora } from '../core/api';
import { AsignacionDia, CATEGORIAS } from '../core/modelos';
import { CamaraComponent } from '../shared/camara.component';
import { MapaComponent, MarcadorMapa } from '../shared/mapa.component';
import { PromotorService } from './promotor.service';

/**
 * Entrada/salida (RF-01, RF-03, RF-04). Iniciar jornada (con foto de entrada,
 * etapa 3) y hacer check-in son
 * acciones separadas; el check-out cierra la visita y la jornada se finaliza
 * aparte. El servidor valida cada acción con la ubicación del momento.
 */
@Component({
  selector: 'app-jornada',
  imports: [MapaComponent, CamaraComponent, FormsModule],
  styles: [`.foto-entrada { display: flex; align-items: center; gap: 10px; } .foto-entrada img { width: 56px; height: 56px; object-fit: cover; border-radius: 50%; }`],
  template: `
    @let h = ps.hoy();
    <app-mapa [marcadores]="marcadores()" alto="230px" />
    <p class="estado-linea">
      ESTADO: <span class="punto" [class.punto--verde]="ps.jornadaAbierta() && !ps.enPausa()"></span>
      {{ ps.enPausa() ? 'En pausa' : ps.jornadaAbierta() ? 'Jornada activa' : (h?.jornada?.estado === 'Finalizada' ? 'Jornada finalizada' : 'Sin jornada') }}
      @if (ps.jornadaPendiente()) { <span class="etiqueta etiqueta--pendiente">Inicio pendiente de sincronizar</span> }
    </p>

    @if (!h) {
      <p class="nota">Cargando tu jornada…</p>
    } @else if (!h.asignaciones.length) {
      <p class="nota">No tienes tiendas asignadas para hoy. Consulta a tu supervisor.</p>
    } @else {
      @if (!ps.jornadaAbierta() && !h.jornada) {
        <p class="nota">Para iniciar debes estar en tu primera tienda: <b>{{ h.asignaciones[0].tienda.nombre_comercial }} {{ h.asignaciones[0].tienda.sucursal }}</b>.</p>
        @if (!ps.jornadaPendiente()) {
          <section class="tarjeta-oscura">
            <h2>Foto de entrada</h2>
            <p class="nota">Tómate una foto con la cámara para registrar tu entrada.</p>
            <app-camara lado="user" (capturada)="foto.set($event)" />
            <div class="fila-botones">
              @if (!foto()) {
                <button type="button" class="boton" (click)="tomar()">📷 CAPTURAR</button>
              } @else {
                <button type="button" class="boton" (click)="repetir()">REPETIR</button>
              }
            </div>
          </section>
          <button type="button" class="boton boton--rojo boton--grande" (click)="iniciar()" [disabled]="ps.ocupado() || !foto()">INICIAR JORNADA</button>
          @if (!foto()) { <p class="nota">Primero captura tu foto de entrada.</p> }
        }
      }

      @let v = ps.visitaEnCurso();
      @if (v) {
        <section class="tarjeta-oscura">
          <h2>En tienda: {{ v.tienda }}</h2>
          @if (v.pendiente) { <p class="etiqueta etiqueta--pendiente">Check-in pendiente de sincronizar: aún no validado</p> }
          <p>Fotos válidas: {{ v.validas.length }}/{{ totalCategorias }} @if (v.pendientes.length) { · {{ v.pendientes.length }} por sincronizar }</p>
          <button type="button" class="boton boton--rojo boton--grande" (click)="irAVisita()">📷 TOMAR FOTOS / CHECK-OUT</button>
        </section>
      }

      <h2 class="subtitulo">Tiendas de hoy</h2>
      <ol class="lista-tiendas">
        @for (a of h.asignaciones; track a.id_asignacion) {
          @let est = ps.estadoTienda(a);
          <li>
            <div>
              <b>{{ a.orden_visita }}. {{ a.tienda.nombre_comercial }} {{ a.tienda.sucursal }}</b>
              <small>{{ a.tienda.direccion_completa }}</small>
              <span class="etiqueta" [class.etiqueta--ok]="est === 'Visitada'" [class.etiqueta--pendiente]="est === 'Pendiente de sincronizar'">{{ est }}</span>
              @if (a.visita) { <small>Entrada {{ hora(a.visita.checkin) }} · Salida {{ hora(a.visita.checkout) }} @if (a.visita.duracion_min != null) { · {{ duracion(a.visita.duracion_min) }} }</small> }
            </div>
            @if (est === 'Por visitar' && ps.jornadaAbierta() && !ps.enPausa() && !v) {
              <button type="button" class="boton boton--rojo" (click)="ps.checkin(a)" [disabled]="ps.ocupado()">CHECK-IN</button>
            }
          </li>
        }
      </ol>

      @if (ps.jornadaAbierta()) {
        @if (!pidiendoMotivo()) {
          <button type="button" class="boton boton--grande" (click)="finalizar()" [disabled]="ps.ocupado() || !!v || ps.enPausa()">FINALIZAR JORNADA</button>
          @if (v) { <p class="nota">Registra el check-out de la tienda actual antes de finalizar.</p> }
        } @else {
          <section class="tarjeta-oscura">
            <p class="alerta">Tiendas pendientes: {{ pendientes().join(', ') }}</p>
            <p class="nota">Tu motivo se enviará a tu supervisor como solicitud de ajuste para que la apruebe o la rechace.</p>
            <label class="campo"><span>Motivo para cerrar con tiendas pendientes:</span>
              <textarea [(ngModel)]="motivo" rows="3"></textarea></label>
            <button type="button" class="boton boton--rojo" (click)="finalizar(true)" [disabled]="motivo.trim().length < 10">CERRAR CON MOTIVO</button>
            <button type="button" class="boton" (click)="pidiendoMotivo.set(false)">CANCELAR</button>
          </section>
        }
      }
      @if (h.jornada?.foto_inicio_url) {
        <p class="nota foto-entrada"><img [src]="h.jornada?.foto_inicio_url" alt="Foto de entrada" /> Entrada registrada a las {{ hora(h.jornada?.inicio) }}</p>
      }
      @if (h.jornada?.estado === 'Finalizada') {
        <p class="nota">Jornada finalizada a las {{ hora(h.jornada?.fin) }}. El seguimiento de ubicación está detenido.</p>
      }
    }
  `,
})
export class JornadaPage {
  readonly ps = inject(PromotorService);
  private readonly router = inject(Router);
  readonly hora = hora;
  readonly duracion = duracion;
  readonly totalCategorias = CATEGORIAS.length;
  readonly pidiendoMotivo = signal(false);
  readonly pendientes = signal<string[]>([]);
  motivo = '';

  readonly marcadores = computed<MarcadorMapa[]>(() => {
    const h = this.ps.hoy();
    if (!h) return [];
    const m: MarcadorMapa[] = h.asignaciones.map((a: AsignacionDia) => ({
      lat: a.tienda.latitud, lon: a.tienda.longitud, radio_m: a.tienda.radio_geocerca_m, tipo: 'tienda',
      color: a.visita?.estado === 'Cerrada' ? '#16a34a' : '#E30613', etiqueta: String(a.orden_visita),
      texto: `${a.orden_visita}. ${a.tienda.nombre_comercial} ${a.tienda.sucursal}`,
    }));
    const u = h.estado.ultima_ubicacion;
    if (u) m.push({ lat: u.latitud, lon: u.longitud, color: '#2563eb', tipo: 'persona', etiqueta: 'Yo', texto: `Última ubicación ${hora(u.fecha_hora)}` });
    return m;
  });

  private readonly camara = viewChild(CamaraComponent);
  readonly foto = signal<{ foto: Blob; ancho: number; alto: number } | null>(null);

  async tomar() { await this.camara()?.capturar(); }

  repetir() {
    this.foto.set(null);
    this.camara()?.repetir();
  }

  async iniciar() {
    const f = this.foto();
    if (!f) return;
    const r = await this.ps.iniciarJornada(f.foto, { ancho: f.ancho, alto: f.alto });
    // Si la foto no pasó la validación, se pide otra.
    if (r?.estado === 'rechazado') this.repetir();
    else if (r) this.foto.set(null);
  }

  irAVisita() { void this.router.navigateByUrl('/promotor/visita'); }

  async finalizar(forzar = false) {
    const r = await this.ps.finalizarJornada(forzar, this.motivo);
    if (r?.estado === 'rechazado' && r.respuesta?.puede_forzar) {
      this.pendientes.set(r.respuesta.pendientes ?? []);
      this.pidiendoMotivo.set(true);
    } else if (r?.estado !== 'rechazado') {
      this.pidiendoMotivo.set(false);
      this.motivo = '';
    }
  }
}
