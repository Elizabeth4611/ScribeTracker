import { HttpErrorResponse } from '@angular/common/http';

/** Mensaje legible a partir de un error HTTP del servidor (RF-23). */
export function mensajeError(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return 'No se pudo conectar con el servidor. Revisa tu conexión.';
    }
    const cuerpo = err.error as { error?: unknown } | null;
    if (cuerpo && typeof cuerpo.error === 'string') {
      return cuerpo.error;
    }
    if (err.status === 413) {
      return 'El archivo es demasiado grande.';
    }
  }
  if (err instanceof Error && err.message) {
    return err.message;
  }
  return 'Ocurrió un error inesperado. Inténtalo de nuevo.';
}

/** Errores por campo que devuelve el servidor en validaciones (400). */
export function erroresCampos(err: unknown): Record<string, string> {
  if (err instanceof HttpErrorResponse) {
    const c = (err.error as { campos?: Record<string, string> } | null)?.campos;
    if (c && typeof c === 'object') {
      return c;
    }
  }
  return {};
}

export function uuid(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Fecha y hora local en formato ISO sin zona (como la guarda el servidor). */
export function ahoraLocalIso(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

export function hoyIso(): string {
  return ahoraLocalIso().slice(0, 10);
}

export function hora(iso: string | null | undefined): string {
  return iso ? iso.slice(11, 16) : '—';
}

export function fechaLarga(iso: string): string {
  const [a, m, d] = iso.slice(0, 10).split('-').map(Number);
  return new Date(a, m - 1, d).toLocaleDateString('es-MX', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
}

export function duracion(min: number | null | undefined): string {
  if (min == null) return '—';
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? `${h} h ${m} min` : `${m} min`;
}
