import { Component, ElementRef, OnDestroy, OnInit, output, signal, viewChild } from '@angular/core';

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
  readonly capturada = output<{ foto: Blob; ancho: number; alto: number }>();
  readonly vista = signal<string | null>(null);
  readonly error = signal<string | null>(null);
  private readonly video = viewChild<ElementRef<HTMLVideoElement>>('video');
  private flujo: MediaStream | null = null;

  ngOnInit() { void this.encender(); }
  ngOnDestroy() { this.apagar(); }

  async encender() {
    this.error.set(null);
    this.vista.set(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      this.error.set('Este navegador no permite usar la cámara. Usa Chrome en http://localhost o HTTPS.');
      return;
    }
    try {
      this.flujo = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } }, audio: false,
      });
      setTimeout(() => { const v = this.video()?.nativeElement; if (v) v.srcObject = this.flujo; });
    } catch {
      this.error.set('No se pudo acceder a la cámara del dispositivo. Revisa el permiso de cámara del navegador.');
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
