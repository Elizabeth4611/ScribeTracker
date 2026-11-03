import { Injectable, inject, signal } from '@angular/core';

import { ahoraLocalIso } from './api';
import { ColaService } from './cola.service';
import { GeoService } from './geo.service';

/**
 * Seguimiento periódico de ubicación (RF-02, RNF-15: cada 5 a 10 min).
 *
 * Solo funciona con la jornada abierta y sin pausa; se detiene al iniciar
 * una pausa o al finalizar la jornada (Limitación 7 del ERS). El servidor
 * también rechaza puntos fuera de jornada o en pausa.
 *
 * Límite técnico: una aplicación web solo puede obtener la ubicación
 * mientras la página está abierta; con el navegador cerrado o en segundo
 * plano el sistema operativo suspende la página. El seguimiento continuo
 * con la app cerrada requiere una app nativa o un contenedor como Capacitor
 * con un complemento de geolocalización en segundo plano.
 */
@Injectable({ providedIn: 'root' })
export class RastreoService {
  private readonly geo = inject(GeoService);
  private readonly cola = inject(ColaService);

  readonly activo = signal(false);
  readonly ultimoEnvio = signal<string | null>(null);
  readonly ultimoError = signal<string | null>(null);
  private temporizador: ReturnType<typeof setInterval> | null = null;
  private intervaloMin = 10;

  actualizar(debeRastrear: boolean, intervaloMin: number) {
    if (debeRastrear && (!this.activo() || intervaloMin !== this.intervaloMin)) {
      this.iniciar(intervaloMin);
    } else if (!debeRastrear && this.activo()) {
      this.detener();
    }
  }

  detener() {
    if (this.temporizador) clearInterval(this.temporizador);
    this.temporizador = null;
    this.activo.set(false);
  }

  private iniciar(intervaloMin: number) {
    this.detener();
    this.intervaloMin = intervaloMin;
    this.activo.set(true);
    this.temporizador = setInterval(() => void this.enviar(), intervaloMin * 60_000);
  }

  private async enviar() {
    try {
      const l = await this.geo.leer();
      const r = await this.cola.ejecutar({
        tipo: 'ubicacion', url: '/api/promotor/ubicaciones', descripcion: 'Ubicación periódica',
        cuerpo: { ...l, capturado_en: ahoraLocalIso() },
      });
      if (r.estado === 'rechazado') {
        // El servidor indica que el rastreo debe estar suspendido.
        this.detener();
      }
      this.ultimoEnvio.set(ahoraLocalIso());
      this.ultimoError.set(null);
    } catch (e) {
      this.ultimoError.set(e instanceof Error ? e.message : 'No se pudo leer la ubicación.');
    }
  }
}
