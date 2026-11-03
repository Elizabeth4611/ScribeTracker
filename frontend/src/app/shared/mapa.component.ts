import { AfterViewInit, Component, ElementRef, OnDestroy, effect, input, output, viewChild } from '@angular/core';
import * as L from 'leaflet';

export interface MarcadorMapa {
  lat: number;
  lon: number;
  color: string;
  texto: string;
  etiqueta?: string;
  radio_m?: number;      // dibuja la geocerca
  tipo?: 'tienda' | 'persona' | 'punto';
}

/**
 * Mapa con Leaflet y teselas de OpenStreetMap (no requiere clave de API).
 * El ERS menciona Google Maps; se usa OpenStreetMap porque Google Maps
 * exige una clave con facturación. Necesita conexión a Internet para las
 * teselas; sin red se muestran los marcadores sobre fondo gris.
 */
@Component({
  selector: 'app-mapa',
  template: `<div #contenedor class="mapa" [style.height]="alto()"></div>`,
  styles: [`.mapa { width: 100%; border-radius: 10px; overflow: hidden; background: #d9dde3; z-index: 0; }`],
})
export class MapaComponent implements AfterViewInit, OnDestroy {
  readonly marcadores = input<MarcadorMapa[]>([]);
  readonly recorrido = input<[number, number][]>([]);
  readonly alto = input('320px');
  readonly seleccionable = input(false);
  readonly seleccion = output<{ lat: number; lon: number }>();

  private readonly contenedor = viewChild.required<ElementRef<HTMLDivElement>>('contenedor');
  private mapa?: L.Map;
  private capa = L.layerGroup();
  private ajustado = '';

  constructor() {
    effect(() => {
      const m = this.marcadores();
      const r = this.recorrido();
      if (this.mapa) this.dibujar(m, r);
    });
  }

  ngAfterViewInit() {
    this.mapa = L.map(this.contenedor().nativeElement, { zoomControl: true, attributionControl: true })
      .setView([21.1250, -101.6860], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '&copy; OpenStreetMap',
    }).addTo(this.mapa);
    this.capa.addTo(this.mapa);
    if (this.seleccionable()) {
      this.mapa.on('click', (e: L.LeafletMouseEvent) => this.seleccion.emit({ lat: e.latlng.lat, lon: e.latlng.lng }));
    }
    this.dibujar(this.marcadores(), this.recorrido());
    setTimeout(() => this.mapa?.invalidateSize(), 150);
  }

  ngOnDestroy() {
    this.mapa?.remove();
  }

  private dibujar(marcadores: MarcadorMapa[], recorrido: [number, number][]) {
    this.capa.clearLayers();
    const puntos: L.LatLngExpression[] = [];
    if (recorrido.length > 1) {
      L.polyline(recorrido, { color: '#2563eb', weight: 4, opacity: 0.8 }).addTo(this.capa);
      recorrido.forEach((p) => puntos.push(p));
    }
    for (const m of marcadores) {
      if (m.radio_m) {
        L.circle([m.lat, m.lon], { radius: m.radio_m, color: m.color, weight: 1, fillOpacity: 0.12 }).addTo(this.capa);
      }
      const html = m.tipo === 'persona'
        ? `<div class="pin-persona" style="background:${m.color}">${m.etiqueta ?? ''}</div>`
        : m.tipo === 'punto'
          ? `<div class="pin-punto" style="background:${m.color}"></div>`
          : `<div class="pin-tienda" style="border-color:${m.color}">${m.etiqueta ?? ''}</div>`;
      const tam: [number, number] = m.tipo === 'punto' ? [12, 12] : [30, 30];
      L.marker([m.lat, m.lon], { icon: L.divIcon({ html, className: 'pin', iconSize: tam, iconAnchor: [tam[0] / 2, tam[1] / 2] }) })
        .bindPopup(m.texto).addTo(this.capa);
      puntos.push([m.lat, m.lon]);
    }
    const firma = JSON.stringify(puntos);
    if (puntos.length && firma !== this.ajustado) {
      this.ajustado = firma;
      this.mapa!.fitBounds(L.latLngBounds(puntos as L.LatLngTuple[]).pad(0.25), { maxZoom: 17 });
    }
  }
}
