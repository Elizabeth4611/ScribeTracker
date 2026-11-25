import { Component, ElementRef, OnDestroy, OnInit, input, output, signal, viewChild } from '@angular/core';

/**
 * Cámara integrada en la interfaz (RF-05). Usa getUserMedia y captura el
 * cuadro actual en un lienzo: no hay selector de archivos ni acceso a la
 * galería. Límite: el navegador no puede garantizar que la cámara no sea
 * virtual, y capturar en vivo no equivale a detectar imágenes hechas con IA.
 */
@Component({
  selector: 'app-camara',
  template: `
    <div class="camara">
      @if (error()) {
        <p class="alerta">{{ error() }}</p>
        <button type="button" class="boton" (click)="encender()">Reintentar</button>
      } @else {
        <video #video autoplay playsinline muted [class.oculto]="!!vista()"></video>
        @if (vista()) { <img [src]="vista()" alt="Fotografía capturada" /> }
      }
    </div>
  `,
  styles: [`
    .camara { background: #000; border-radius: 10px; overflow: hidden; min-height: 220px; display: grid; place-items: center; }
    video, img { width: 100%; max-height: 52vh; object-fit: contain; display: block; }
    .oculto { display: none; }
  `],
})
export class CamaraComponent implements OnInit, OnDestroy {
  /** 'user' = cámara frontal (foto de entrada del promotor); 'environment' = trasera (evidencias). */
  readonly lado = input<'user' | 'environment'>('environment');
  readonly capturada = output<{ foto: Blob; ancho: number; alto: number }>();
  readonly vista = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  private readonly video = viewChild<ElementRef<HTMLVideoElement>>('video');
  private flujo: MediaStream | null = null;
  private destruido = false;
  // Corrección F14 (prueba en celular real): en Android solo una pestaña puede
  // usar la cámara. Si otra pestaña de ScribeTracker la dejaba encendida, esta
  // fallaba con un mensaje genérico. Ahora la cámara se apaga al salir de la
  // pantalla o al pasar la pestaña a segundo plano, y se enciende al volver.
  private readonly alCambiarVisibilidad = () => {
    if (document.hidden) this.apagar();
    else if (!this.flujo && !this.vista() && !this.destruido) void this.encender();
  };

  ngOnInit() {
    document.addEventListener('visibilitychange', this.alCambiarVisibilidad);
    void this.encender();
  }

  ngOnDestroy() {
    this.destruido = true;
    document.removeEventListener('visibilitychange', this.alCambiarVisibilidad);
    this.apagar();
  }

  async encender() {
    this.error.set(null);
    this.vista.set(null);
    this.apagar();
    if (!navigator.mediaDevices?.getUserMedia) {
      this.error.set('Este navegador no permite usar la cámara. Abre el sistema con HTTPS.');
      return;
    }
    try {
      const flujo = await this.pedir({ facingMode: { ideal: this.lado() }, width: { ideal: 1280 } });
      if (this.destruido || document.hidden) {   // se salió de la pantalla mientras esperaba el permiso
        flujo.getTracks().forEach((t) => t.stop());
        return;
      }
      this.flujo = flujo;
      setTimeout(() => { const v = this.video()?.nativeElement; if (v) v.srcObject = this.flujo; });
    } catch (e) {
      this.error.set(mensajeCamara(e));
    }
  }

  /** Pide la cámara indicada; si ese lado no existe, cualquier cámara disponible. */
  private async pedir(video: MediaTrackConstraints): Promise<MediaStream> {
    try {
      return await navigator.mediaDevices.getUserMedia({ video, audio: false });
    } catch (e) {
      if ((e as DOMException)?.name === 'OverconstrainedError') {
        return navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }
      throw e;
    }
  }

  /** Toma la foto del cuadro actual del video. */
  capturar(): Promise<boolean> {
    const v = this.video()?.nativeElement;
    if (!v || !v.videoWidth) return Promise.resolve(false);
    const escala = Math.min(1, 1280 / v.videoWidth);
    const lienzo = document.createElement('canvas');
    lienzo.width = Math.round(v.videoWidth * escala);
    lienzo.height = Math.round(v.videoHeight * escala);
    lienzo.getContext('2d')!.drawImage(v, 0, 0, lienzo.width, lienzo.height);
    return new Promise((resolve) => lienzo.toBlob((b) => {
      if (!b) { resolve(false); return; }
      this.vista.set(lienzo.toDataURL('image/jpeg', 0.6));
      this.capturada.emit({ foto: b, ancho: lienzo.width, alto: lienzo.height });
      resolve(true);
    }, 'image/jpeg', 0.85));
  }

  repetir() { this.vista.set(null); }

  private apagar() {
    this.flujo?.getTracks().forEach((t) => t.stop());
    this.flujo = null;
  }
}

function mensajeCamara(e: unknown): string {
  switch ((e as DOMException)?.name) {
    case 'NotAllowedError':
    case 'SecurityError':
      return 'El navegador no tiene permiso para usar la cámara. Toca el candado o el ícono junto a la dirección → Permisos → Cámara → Permitir, y luego Reintentar.';
    case 'NotReadableError':
    case 'AbortError':
      return 'La cámara está ocupada por otra pestaña o aplicación. Cierra las otras pestañas de ScribeTracker y las apps que usen la cámara, y toca Reintentar.';
    case 'NotFoundError':
      return 'No se encontró ninguna cámara en este dispositivo.';
    default:
      return 'No se pudo acceder a la cámara del dispositivo. Revisa el permiso de cámara del navegador y toca Reintentar.';
  }
}
