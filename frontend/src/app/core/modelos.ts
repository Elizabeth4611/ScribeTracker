export type Rol = 'Promotor' | 'Supervisor' | 'Administrador';
export type Estatus = 'Activo' | 'Inactivo';

export interface Usuario {
  id_usuario: number;
  nombre_completo: string;
  correo_electronico: string;
  telefono: string | null;
  rol: Rol;
  estatus: Estatus;
  numero_empleado: string | null;
  tipo_contrato: string | null;
  fecha_alta: string | null;
  id_supervisor: number | null;
  nombre_supervisor: string | null;
  debe_cambiar_password: boolean;
}

/** Pantalla inicial de cada rol. */
export const RUTA_INICIO: Record<Rol, string> = {
  Promotor: '/promotor',
  Supervisor: '/panel/supervision',
  Administrador: '/panel/inicio',
};

export const CATEGORIAS = ['Anaquel antes', 'Anaquel después', 'Precios', 'Promociones'] as const;
export type Categoria = (typeof CATEGORIAS)[number];

export interface Tienda {
  id_tienda: number;
  nombre_comercial: string;
  cadena: string;
  sucursal: string;
  direccion_completa: string;
  zona: string | null;
  latitud: number;
  longitud: number;
  radio_geocerca_m: number;
  tiempo_estimado_min: number | null;
  estatus: 'Activa' | 'Inactiva';
}

export interface Evidencia {
  id_evidencia: number;
  id_visita: number;
  categoria: Categoria;
  sin_promocion: boolean;
  fecha_hora_captura: string;
  fecha_hora_recepcion: string;
  latitud: number;
  longitud: number;
  precision_m: number | null;
  distancia_m: number;
  dentro_geocerca: boolean;
  estatus_validacion: 'Válida' | 'Fuera de geocerca' | 'Rechazada';
  motivo_validacion: string | null;
  revision_supervisor: string;
  comentario_revision: string | null;
  hash_imagen: string;
  origen: string;
  url: string;
}

export interface Visita {
  id_visita: number;
  id_asignacion: number;
  estado: 'Abierta' | 'Cerrada';
  id_cliente: string | null;
  tienda: Tienda;
  checkin: string;
  distancia_checkin_m: number;
  latitud_checkin: number;
  longitud_checkin: number;
  checkout: string | null;
  distancia_checkout_m: number | null;
  latitud_checkout: number | null;
  longitud_checkout: number | null;
  duracion_min: number | null;
  origen: string;
  categorias_validas: Categoria[];
  categorias_faltantes: Categoria[];
  evidencias: Evidencia[];
  nombre_promotor?: string;
}

export interface Pausa {
  id_pausa: number;
  tipo: 'Comida' | 'Descanso';
  inicio: string;
  fin: string | null;
  duracion_programada_min: number;
  duracion_real_min: number;
}

export interface Jornada {
  id_jornada: number;
  fecha: string;
  estado: 'Abierta' | 'Finalizada';
  inicio: string;
  fin: string | null;
  distancia_inicio_m: number;
  cierre_forzado: boolean;
  motivo_cierre: string | null;
  origen: string;
  pausas: Pausa[];
}

export interface AsignacionDia {
  id_asignacion: number;
  orden_visita: number;
  tienda: Tienda;
  visita: Visita | null;
}

export interface EstadoPromotor {
  estado_cuenta: Estatus;
  estado_jornada: 'Sin jornada' | 'En jornada' | 'En pausa' | 'Finalizada';
  estado_visita: 'En tienda' | 'En traslado' | null;
  estado_conexion: 'Reciente' | 'Desactualizada' | 'Sin ubicación' | 'Rastreo suspendido';
  tienda_actual: string | null;
  ultima_ubicacion: { latitud: number; longitud: number; precision_m: number | null; fecha_hora: string } | null;
  pausa: { tipo: string; inicio: string; duracion_programada_min: number } | null;
}

export interface ResumenDia {
  fecha: string;
  jornada: Jornada | null;
  asignaciones: AsignacionDia[];
  resumen: {
    tiendas_asignadas: number;
    tiendas_visitadas: number;
    minutos_en_tienda: number;
    minutos_en_pausa: number;
    fotos: number;
  };
}

export interface HoyPromotor extends ResumenDia {
  estado: EstadoPromotor;
  rastreo_activo: boolean;
  gps_intervalo_min: number;
  pausas_disponibles: { Comida: number; Descanso: number };
  hora_servidor: string;
}

export interface Incidencia {
  id_incidencia: number;
  id_promotor: number;
  nombre_promotor: string | null;
  tipo: string;
  es_critica: boolean;
  fecha_hora: string;
  descripcion: string | null;
  estado: 'Pendiente' | 'Revisada' | 'Sancionada';
  origen: string;
  id_visita: number | null;
  id_evidencia: number | null;
  comentario_revision: string | null;
  fecha_hora_revision: string | null;
}

export interface PromotorOpcion {
  id_usuario: number;
  nombre_completo: string;
  numero_empleado: string | null;
  estatus: Estatus;
  tipo_contrato: string | null;
}

export interface Ruta {
  id_ruta: number;
  nombre_ruta: string;
  id_promotor: number;
  nombre_promotor: string | null;
  dias_programados: string[];
  estado: 'Activa' | 'Inactiva';
  tiendas: (Tienda & { orden_visita: number })[];
}

export interface Parametro {
  clave: string;
  descripcion: string;
  tipo_dato: string;
  valor_activo: string;
  valor_default: string;
  rango: string | null;
  categoria: string;
  fecha_modificacion: string;
}

export interface ReporteInfo {
  id_reporte: number;
  tipo: 'Diario' | 'Semanal' | 'Mensual';
  contenido: 'Desempeño' | 'Incidencias' | 'Exhibición';
  fecha_generacion: string;
  desde: string;
  hasta: string;
  id_promotor: number | null;
  promotor: string;
  generado_por: string | null;
  formato: string;
}
