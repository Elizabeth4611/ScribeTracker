import { Injectable, signal } from '@angular/core';

export interface Aviso {
  id: number;
  tipo: 'ok' | 'error' | 'info' | 'alerta';
  texto: string;
}

/** Mensajes de confirmación (RF-22) y de error (RF-23). */
@Injectable({ providedIn: 'root' })
export class AvisosService {
  private siguiente = 1;
  readonly lista = signal<Aviso[]>([]);

  ok(texto: string) { this.mostrar('ok', texto); }
  error(texto: string) { this.mostrar('error', texto, 7000); }
  info(texto: string) { this.mostrar('info', texto); }
  alerta(texto: string) { this.mostrar('alerta', texto, 7000); }

  quitar(id: number) {
    this.lista.update((l) => l.filter((a) => a.id !== id));
  }

  private mostrar(tipo: Aviso['tipo'], texto: string, ms = 4500) {
    const id = this.siguiente++;
    this.lista.update((l) => [...l.slice(-3), { id, tipo, texto }]);
    setTimeout(() => this.quitar(id), ms);
  }
}
