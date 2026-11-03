import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ahoraLocalIso, mensajeError, uuid } from './api';

/**
 * Cola de eventos del promotor (RNF-08 / RNF-09: funcionamiento sin conexión).
 *
 * Cada acción se guarda primero en IndexedDB con un identificador generado
 * en el dispositivo (X-Id-Cliente) y la hora de captura. Después se envía al
 * servidor en el orden en que ocurrió. Si no hay red, queda "pendiente" y se
 * reintenta al recuperar la conexión; el servidor valida cada evento al
 * recibirlo y, como el identificador se repite en cada reintento, no se
 * duplica. Un evento pendiente nunca se muestra como validado: solo pasa a
 * "confirmado" con la respuesta del servidor.
 */

export type TipoEvento =
  | 'jornada_iniciar' | 'jornada_finalizar' | 'checkin' | 'checkout'
  | 'evidencia' | 'pausa_iniciar' | 'pausa_finalizar' | 'ubicacion';

export interface Evento {
  id: string;
  id_usuario: number;
  tipo: TipoEvento;
  url: string;
  descripcion: string;
  cuerpo?: Record<string, unknown>;
  formulario?: Record<string, string>;
  foto?: Blob;
  capturado_en: string;
  creado: number;
  estado: 'pendiente' | 'rechazado';
  diferido: boolean;
  intentos: number;
  mensaje?: string;
  ref?: { id_asignacion?: number; visita_cliente?: string; id_visita?: number; categoria?: string };
}

export type Resultado =
  | { estado: 'confirmado'; codigo: number; respuesta: any }
  | { estado: 'pendiente' }
  | { estado: 'rechazado'; codigo: number; mensaje: string; respuesta: any };

const BD = 'scribetracker';
const ALMACEN = 'eventos';
const CACHE = 'cache';

function abrir(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const r = indexedDB.open(BD, 1);
    r.onupgradeneeded = () => {
      const db = r.result;
      if (!db.objectStoreNames.contains(ALMACEN)) {
        db.createObjectStore(ALMACEN, { keyPath: 'id' }).createIndex('creado', 'creado');
      }
      if (!db.objectStoreNames.contains(CACHE)) {
        db.createObjectStore(CACHE, { keyPath: 'clave' });
      }
    };
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
}

async function operar<T>(almacen: string, modo: IDBTransactionMode, fn: (s: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await abrir();
  return new Promise<T>((resolve, reject) => {
    const tx = db.transaction(almacen, modo);
    const req = fn(tx.objectStore(almacen));
    tx.oncomplete = () => { resolve(req.result); db.close(); };
    tx.onerror = () => { reject(tx.error); db.close(); };
  });
}

@Injectable({ providedIn: 'root' })
export class ColaService {
  private readonly http = inject(HttpClient);

  readonly eventos = signal<Evento[]>([]);
  readonly pendientes = computed(() => this.eventos().filter((e) => e.estado === 'pendiente'));
  readonly rechazados = computed(() => this.eventos().filter((e) => e.estado === 'rechazado'));
  readonly enLinea = signal(typeof navigator === 'undefined' ? true : navigator.onLine);
  readonly sincronizando = signal(false);
  readonly ultimaSincronizacion = signal<string | null>(null);

  private usuario = 0;
  private enCurso: Promise<void> | null = null;
  private readonly oyentes: (() => void)[] = [];

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => { this.enLinea.set(true); void this.sincronizar(); });
      window.addEventListener('offline', () => this.enLinea.set(false));
      setInterval(() => { if (this.pendientes().length) void this.sincronizar(); }, 30000);
    }
  }

  /**
   * Corrección F08: avisa a quien muestra datos del servidor que la
   * sincronización terminó, para que vuelva a leerlos. Antes la pantalla
   * seguía con la copia local hasta el refresco de 60 s.
   */
  alSincronizar(oyente: () => void) {
    this.oyentes.push(oyente);
  }

  /** Se llama al iniciar sesión: solo se sincronizan eventos de ese usuario. */
  async activar(idUsuario: number) {
    this.usuario = idUsuario;
    await this.recargar();
    void this.sincronizar();
  }

  desactivar() {
    this.usuario = 0;
    this.eventos.set([]);
  }

  async recargar() {
    try {
      const todos = await operar<Evento[]>(ALMACEN, 'readonly', (s) => s.getAll() as IDBRequest<Evento[]>);
      this.eventos.set(todos.filter((e) => e.id_usuario === this.usuario).sort((a, b) => a.creado - b.creado));
    } catch {
      this.eventos.set([]);
    }
  }

  /** Guarda el evento y lo envía si es el siguiente en la fila. */
  async ejecutar(datos: {
    tipo: TipoEvento; url: string; descripcion: string; cuerpo?: Record<string, unknown>;
    formulario?: Record<string, string>; foto?: Blob; ref?: Evento['ref']; id?: string;
  }): Promise<Resultado> {
    const capturado_en = (datos.cuerpo?.['capturado_en'] as string) ?? datos.formulario?.['capturado_en'] ?? ahoraLocalIso();
    const ev: Evento = {
      id: datos.id ?? uuid(), id_usuario: this.usuario, tipo: datos.tipo, url: datos.url,
      descripcion: datos.descripcion, capturado_en, creado: Date.now(), estado: 'pendiente',
      diferido: false, intentos: 0, ref: datos.ref,
      cuerpo: datos.cuerpo ? { ...datos.cuerpo, capturado_en } : undefined,
      formulario: datos.formulario ? { ...datos.formulario, capturado_en } : undefined,
      foto: datos.foto,
    };
    await this.guardar(ev);
    await this.recargar();

    // Si hay eventos anteriores sin enviar, se respeta el orden.
    const anteriores = this.pendientes().filter((e) => e.creado < ev.creado || (e.creado === ev.creado && e.id !== ev.id));
    if (anteriores.length) {
      await this.marcarDiferido(ev);
      void this.sincronizar();
      return { estado: 'pendiente' };
    }
    return this.enviar(ev);
  }

  /** Envía los pendientes en orden de captura. Se detiene al fallar la red. */
  sincronizar(): Promise<void> {
    if (this.enCurso) return this.enCurso;
    // Corrección F07: antes, sin pendientes, la función terminaba de forma
    // síncrona y su "finally" limpiaba enCurso antes de que se asignara la
    // promesa; enCurso quedaba ocupado y no se volvía a sincronizar nunca.
    const ejecucion = (async () => {
      this.sincronizando.set(true);
      try {
        // Se repite mientras haya avance: así también salen los eventos que
        // se agregaron durante la sincronización.
        let seguir = true;
        while (seguir && this.pendientes().length) {
          seguir = false;
          for (const ev of [...this.pendientes()]) {
            const r = await this.enviar(ev);
            if (r.estado === 'pendiente') { seguir = false; break; }
            seguir = true;
          }
        }
        this.ultimaSincronizacion.set(ahoraLocalIso());
      } finally {
        this.sincronizando.set(false);
      }
      for (const oyente of this.oyentes) oyente();
    })();
    this.enCurso = ejecucion;
    void ejecucion.finally(() => {
      if (this.enCurso === ejecucion) this.enCurso = null;
    });
    return ejecucion;
  }

  async descartar(id: string) {
    await operar(ALMACEN, 'readwrite', (s) => s.delete(id));
    await this.recargar();
  }

  /** Copia local de la última respuesta de /hoy para trabajar sin red. */
  async guardarCache(clave: string, valor: unknown) {
    try {
      await operar(CACHE, 'readwrite', (s) => s.put({ clave: `${this.usuario}:${clave}`, valor }));
    } catch { /* almacenamiento no disponible */ }
  }

  async leerCache<T>(clave: string): Promise<T | null> {
    try {
      const r = await operar<{ valor: T } | undefined>(CACHE, 'readonly', (s) => s.get(`${this.usuario}:${clave}`) as IDBRequest<{ valor: T } | undefined>);
      return r?.valor ?? null;
    } catch {
      return null;
    }
  }

  // ------------------------------------------------------------ interno

  private async enviar(ev: Evento): Promise<Resultado> {
    let headers = new HttpHeaders({ 'X-Id-Cliente': ev.id });
    if (ev.diferido) headers = headers.set('X-Origen', 'sin-conexion');
    let cuerpo: unknown = ev.cuerpo ?? {};
    if (ev.formulario) {
      const fd = new FormData();
      Object.entries(ev.formulario).forEach(([k, v]) => fd.append(k, v));
      if (ev.foto) fd.append('foto', ev.foto, 'captura.jpg');
      cuerpo = fd;
    }
    try {
      const resp = await firstValueFrom(this.http.post(ev.url, cuerpo, { headers, observe: 'response' }));
      await this.descartar(ev.id);
      this.enLinea.set(true);
      return { estado: 'confirmado', codigo: resp.status, respuesta: resp.body };
    } catch (err) {
      const e = err as HttpErrorResponse;
      // 422: la foto se guardó pero no cuenta (fuera de geocerca o repetida).
      if (e instanceof HttpErrorResponse && e.status === 422) {
        await this.descartar(ev.id);
        return { estado: 'confirmado', codigo: 422, respuesta: e.error };
      }
      // Sin red, error del servidor o sesión vencida: se reintenta después.
      if (!(e instanceof HttpErrorResponse) || e.status === 0 || e.status >= 500 || e.status === 401) {
        if (e instanceof HttpErrorResponse && e.status === 0) this.enLinea.set(false);
        await this.marcarDiferido(ev);
        return { estado: 'pendiente' };
      }
      // Regla de negocio: el servidor rechazó el evento.
      const actualizado: Evento = { ...ev, estado: 'rechazado', mensaje: mensajeError(e), intentos: ev.intentos + 1, foto: undefined };
      await this.guardar(actualizado);
      await this.recargar();
      return { estado: 'rechazado', codigo: e.status, mensaje: actualizado.mensaje!, respuesta: e.error };
    }
  }

  private async marcarDiferido(ev: Evento) {
    await this.guardar({ ...ev, diferido: true, intentos: ev.intentos + 1 });
    await this.recargar();
  }

  private guardar(ev: Evento) {
    return operar(ALMACEN, 'readwrite', (s) => s.put(ev));
  }
}
