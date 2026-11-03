import { EstadoPromotor } from '../core/modelos';

/**
 * Colores del mapa del supervisor (prototipo): verde activo, amarillo en
 * traslado, rojo en pausa, negro desconectado. Gris: sin jornada o finalizada.
 */
export function colorEstado(e: EstadoPromotor): string {
  if (e.estado_jornada === 'En pausa') return '#dc2626';
  if (e.estado_jornada === 'En jornada') {
    if (e.estado_conexion === 'Desactualizada' || e.estado_conexion === 'Sin ubicación') return '#111827';
    return e.estado_visita === 'En tienda' ? '#16a34a' : '#eab308';
  }
  return '#9ca3af';
}

export function textoEstado(e: EstadoPromotor): string {
  if (e.estado_jornada === 'En jornada') {
    const c = e.estado_conexion === 'Reciente' ? '' : ` · ubicación ${e.estado_conexion.toLowerCase()}`;
    return `${e.estado_visita}${e.tienda_actual ? ': ' + e.tienda_actual : ''}${c}`;
  }
  return e.estado_jornada;
}
