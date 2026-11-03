import { Injectable } from '@angular/core';

export interface Lectura {
  latitud: number;
  longitud: number;
  precision: number;
}

/**
 * Ubicación del dispositivo (API de Geolocalización del navegador).
 * Requiere contexto seguro: funciona en http://localhost o con HTTPS.
 * El navegador no permite detectar aplicaciones de GPS simulado.
 */
@Injectable({ providedIn: 'root' })
export class GeoService {
  leer(): Promise<Lectura> {
    return new Promise((resolve, reject) => {
      if (!('geolocation' in navigator)) {
        reject(new Error('Este navegador no permite obtener la ubicación.'));
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (p) => resolve({
          latitud: p.coords.latitude,
          longitud: p.coords.longitude,
          precision: Math.round(p.coords.accuracy * 10) / 10,
        }),
        (e) => reject(new Error(
          e.code === e.PERMISSION_DENIED
            ? 'Para registrar tu ubicación, permite el acceso a la ubicación en el navegador.'
            : e.code === e.TIMEOUT
              ? 'No se obtuvo la ubicación a tiempo. Activa el GPS e intenta de nuevo.'
              : 'Para registrar tu ubicación, activa el GPS de tu dispositivo.',
        )),
        { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
      );
    });
  }
}
