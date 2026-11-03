import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ahoraLocalIso, mensajeError } from '../core/api';
import { AvisosService } from '../core/avisos.service';
import { ColaService, Resultado } from '../core/cola.service';
import { GeoService } from '../core/geo.service';
import { AsignacionDia, CATEGORIAS, Categoria, HoyPromotor } from '../core/modelos';
import { RastreoService } from '../core/rastreo.service';

/** Visita en curso: confirmada por el servidor o solo registrada en el dispositivo. */
export interface VisitaEnCurso {
  id_asignacion: number;
  id_visita: number | null;
  visita_cliente: string | null;
  tienda: string;
  pendiente: boolean;
  validas: Categoria[];
  pendientes: Categoria[];
}

/**
 * Estado del día del promotor. Lo confirmado viene de /api/promotor/hoy;
 * lo que aún no llega al servidor se muestra aparte como "pendiente de
 * sincronizar" y nunca como validado.
 */
@Injectable({ providedIn: 'root' })
export class PromotorService {
  private readonly http = inject(HttpClient);
  private readonly geo = inject(GeoService);
  readonly cola = inject(ColaService);
  private readonly rastreo = inject(RastreoService);
  private readonly avisos = inject(AvisosService);

  readonly hoy = signal<HoyPromotor | null>(null);
  readonly desdeCache = signal(false);
  readonly ocupado = signal(false);

  constructor() {
    // F08: al terminar de sincronizar, se vuelve a leer el estado del servidor.
    this.cola.alSincronizar(() => { if (this.cola.enLinea()) void this.cargar(); });
  }

  readonly jornadaPendiente = computed(() => this.cola.pendientes().some((e) => e.tipo === 'jornada_iniciar'));
  readonly finPendiente = computed(() => this.cola.pendientes().some((e) => e.tipo === 'jornada_finalizar'));
  readonly pausaPendiente = computed(() => {
    const p = this.cola.pendientes().filter((e) => e.tipo === 'pausa_iniciar' || e.tipo === 'pausa_finalizar');
    return p.length ? p[p.length - 1] : null;
  });

  readonly jornadaAbierta = computed(() =>
    (this.hoy()?.jornada?.estado === 'Abierta' || this.jornadaPendiente()) && !this.finPendiente());

  readonly enPausa = computed(() => {
    const p = this.pausaPendiente();
    if (p) return p.tipo === 'pausa_iniciar';
    return this.hoy()?.estado.estado_jornada === 'En pausa';
  });

  readonly visitaEnCurso = computed<VisitaEnCurso | null>(() => {
    const h = this.hoy();
    const pend = this.cola.pendientes();
    const salidaPendiente = (idVisita: number | null, cliente: string | null) =>
      pend.some((e) => e.tipo === 'checkout' && ((idVisita && e.ref?.id_visita === idVisita) || (cliente && e.ref?.visita_cliente === cliente)));
    const fotosPend = (idVisita: number | null, cliente: string | null) => pend
      .filter((e) => e.tipo === 'evidencia' && ((idVisita && e.ref?.id_visita === idVisita) || (cliente && e.ref?.visita_cliente === cliente)))
      .map((e) => e.ref!.categoria as Categoria);

    const abierta = h?.asignaciones.find((a) => a.visita?.estado === 'Abierta');
    if (abierta?.visita && !salidaPendiente(abierta.visita.id_visita, abierta.visita.id_cliente)) {
      return {
        id_asignacion: abierta.id_asignacion, id_visita: abierta.visita.id_visita, visita_cliente: abierta.visita.id_cliente,
        tienda: `${abierta.tienda.nombre_comercial} ${abierta.tienda.sucursal}`, pendiente: false,
        validas: abierta.visita.categorias_validas, pendientes: fotosPend(abierta.visita.id_visita, abierta.visita.id_cliente),
      };
    }
    const ci = pend.find((e) => e.tipo === 'checkin' && !salidaPendiente(null, e.id));
    if (ci) {
      const a = h?.asignaciones.find((x) => x.id_asignacion === ci.ref?.id_asignacion);
      return {
        id_asignacion: ci.ref!.id_asignacion!, id_visita: null, visita_cliente: ci.id,
        tienda: a ? `${a.tienda.nombre_comercial} ${a.tienda.sucursal}` : 'Tienda', pendiente: true,
        validas: [], pendientes: fotosPend(null, ci.id),
      };
    }
    return null;
  });

  /** Estado de cada tienda asignada para la lista de la jornada. */
  estadoTienda(a: AsignacionDia): 'Visitada' | 'En curso' | 'Pendiente de sincronizar' | 'Por visitar' {
    if (a.visita?.estado === 'Cerrada') return 'Visitada';
    const pend = this.cola.pendientes();
    if (a.visita?.estado === 'Abierta') {
      return pend.some((e) => e.tipo === 'checkout' && e.ref?.id_visita === a.visita!.id_visita) ? 'Pendiente de sincronizar' : 'En curso';
    }
    return pend.some((e) => e.tipo === 'checkin' && e.ref?.id_asignacion === a.id_asignacion) ? 'Pendiente de sincronizar' : 'Por visitar';
  }

  async cargar(): Promise<void> {
    try {
      const h = await firstValueFrom(this.http.get<HoyPromotor>('/api/promotor/hoy'));
      this.hoy.set(h);
      this.desdeCache.set(false);
      await this.cola.guardarCache('hoy', h);
    } catch {
      const c = await this.cola.leerCache<HoyPromotor>('hoy');
      if (c) {
        this.hoy.set(c);
        this.desdeCache.set(true);
      }
    }
    this.actualizarRastreo();
  }

  actualizarRastreo() {
    const h = this.hoy();
    this.rastreo.actualizar(this.jornadaAbierta() && !this.enPausa(), h?.gps_intervalo_min ?? 10);
  }

  // --------------------------------------------------------------- acciones

  iniciarJornada() {
    return this.conUbicacion('jornada_iniciar', '/api/promotor/jornada/iniciar', 'Inicio de jornada', {});
  }

  finalizarJornada(forzar = false, motivo = '') {
    return this.conUbicacion('jornada_finalizar', '/api/promotor/jornada/finalizar', 'Fin de jornada', { forzar, motivo });
  }

  checkin(a: AsignacionDia) {
    return this.conUbicacion('checkin', '/api/promotor/visitas/checkin', `Check-in ${a.tienda.nombre_comercial}`,
      { id_asignacion: a.id_asignacion }, { id_asignacion: a.id_asignacion });
  }

  checkout(v: VisitaEnCurso) {
    const ref = v.id_visita ? { id_visita: v.id_visita } : { visita_cliente: v.visita_cliente! };
    return this.conUbicacion('checkout', '/api/promotor/visitas/checkout', `Check-out ${v.tienda}`, ref, ref);
  }

  async pausa(accion: 'iniciar' | 'finalizar', tipo?: 'Comida' | 'Descanso') {
    this.ocupado.set(true);
    try {
      const r = await this.cola.ejecutar({
        tipo: accion === 'iniciar' ? 'pausa_iniciar' : 'pausa_finalizar',
        url: `/api/promotor/pausas/${accion}`,
        descripcion: accion === 'iniciar' ? `Pausa de ${tipo?.toLowerCase()}` : 'Fin de pausa',
        cuerpo: { tipo, capturado_en: ahoraLocalIso() },
      });
      return this.informar(r);
    } finally {
      this.ocupado.set(false);
      await this.cargar();
    }
  }

  async subirFoto(v: VisitaEnCurso, categoria: Categoria, foto: Blob, meta: Record<string, unknown>, sinPromocion: boolean) {
    this.ocupado.set(true);
    try {
      const l = await this.geo.leer();
      const formulario: Record<string, string> = {
        categoria, latitud: String(l.latitud), longitud: String(l.longitud), precision: String(l.precision),
        metadatos: JSON.stringify({ ...meta, fuente: 'camara', agente: navigator.userAgent, fecha_dispositivo: ahoraLocalIso() }),
        capturado_en: ahoraLocalIso(), sin_promocion: sinPromocion ? '1' : '0',
      };
      if (v.id_visita) formulario['id_visita'] = String(v.id_visita);
      else formulario['visita_cliente'] = v.visita_cliente!;
      const r = await this.cola.ejecutar({
        tipo: 'evidencia', url: '/api/promotor/evidencias', descripcion: `Foto ${categoria} · ${v.tienda}`,
        formulario, foto, ref: { id_visita: v.id_visita ?? undefined, visita_cliente: v.visita_cliente ?? undefined, categoria },
      });
      return this.informar(r);
    } catch (e) {
      this.avisos.error(mensajeError(e));
      return null;
    } finally {
      this.ocupado.set(false);
      await this.cargar();
    }
  }

  /** Lee la ubicación, guarda el evento en la cola y lo envía. */
  private async conUbicacion(tipo: any, url: string, descripcion: string, extra: Record<string, unknown>, ref?: any) {
    this.ocupado.set(true);
    try {
      const l = await this.geo.leer();
      const r = await this.cola.ejecutar({ tipo, url, descripcion, cuerpo: { ...l, ...extra, capturado_en: ahoraLocalIso() }, ref });
      return this.informar(r);
    } catch (e) {
      this.avisos.error(mensajeError(e));
      return null;
    } finally {
      this.ocupado.set(false);
      await this.cargar();
    }
  }

  private informar(r: Resultado): Resultado {
    if (r.estado === 'confirmado') {
      const msg = r.respuesta?.mensaje ?? 'Registrado correctamente.';
      if (r.codigo === 422) this.avisos.alerta(msg); else this.avisos.ok(msg);
    } else if (r.estado === 'pendiente') {
      this.avisos.info('Sin conexión: se guardó en el teléfono y se enviará al recuperar la señal. Aún no está validado por el servidor.');
    } else {
      this.avisos.error(r.mensaje);
    }
    return r;
  }

  faltantes(v: VisitaEnCurso): Categoria[] {
    return CATEGORIAS.filter((c) => !v.validas.includes(c) && !v.pendientes.includes(c));
  }
}
