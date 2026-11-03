import { Component, OnDestroy, computed, inject, signal } from '@angular/core';

import { PromotorService } from './promotor.service';

/** Pausas programadas (RF-08): 1 comida de 60 min y 2 descansos de 20 min. */
@Component({
  selector: 'app-pausas',
  template: `
    @let h = ps.hoy();
    <p class="estado-linea">ESTADO: {{ ps.enPausa() ? 'EN PAUSA' : ps.jornadaAbierta() ? 'ACTIVO' : 'SIN JORNADA' }}
      <span class="punto" [class.punto--verde]="ps.jornadaAbierta() && !ps.enPausa()"></span></p>
    <p class="centro">TEMPORIZADOR:</p>
    <div class="temporizador" [class.excedido]="excedido()">{{ reloj() }}</div>
    @if (h?.estado?.pausa; as p) {
      <p class="centro">Pausa de {{ p.tipo.toLowerCase() }} · programada {{ p.duracion_programada_min }} min</p>
    }
    @if (ps.pausaPendiente()) { <p class="etiqueta etiqueta--pendiente">Cambio de pausa pendiente de sincronizar</p> }
    @if (!ps.enPausa()) {
      <button type="button" class="boton boton--blanco" (click)="ps.pausa('iniciar', 'Comida')"
        [disabled]="!ps.jornadaAbierta() || ps.ocupado() || (h?.pausas_disponibles?.Comida ?? 0) < 1">COMIDA ({{ h?.pausas_disponibles?.Comida ?? 0 }})</button>
      <button type="button" class="boton boton--blanco" (click)="ps.pausa('iniciar', 'Descanso')"
        [disabled]="!ps.jornadaAbierta() || ps.ocupado() || (h?.pausas_disponibles?.Descanso ?? 0) < 1">DESCANSO ({{ h?.pausas_disponibles?.Descanso ?? 0 }})</button>
    } @else {
      <button type="button" class="boton boton--rojo boton--grande" (click)="ps.pausa('finalizar')" [disabled]="ps.ocupado()">FINALIZAR</button>
    }
    <p class="nota">Durante la pausa el seguimiento de ubicación se detiene y no se registran visitas ni fotos.</p>
  `,
})
export class PausasPage implements OnDestroy {
  readonly ps = inject(PromotorService);
  private readonly ahora = signal(Date.now());
  private readonly t = setInterval(() => this.ahora.set(Date.now()), 1000);

  private readonly segundos = computed(() => {
    const p = this.ps.hoy()?.estado?.pausa;
    if (!p || !this.ps.enPausa()) return 0;
    const [f, h] = p.inicio.split('T');
    const [a, m, d] = f.split('-').map(Number);
    const [hh, mm, ss] = h.split(':').map(Number);
    return Math.max(0, Math.floor((this.ahora() - new Date(a, m - 1, d, hh, mm, ss).getTime()) / 1000));
  });

  readonly reloj = computed(() => {
    const s = this.segundos();
    return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
  });

  readonly excedido = computed(() => {
    const p = this.ps.hoy()?.estado?.pausa;
    return !!p && this.segundos() > p.duracion_programada_min * 60;
  });

  ngOnDestroy() { clearInterval(this.t); }
}
