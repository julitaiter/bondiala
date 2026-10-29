import type { MultiLineString } from "geojson";
export type Theme = "light" | "dark" | "system";
export type Palette = {
  color_principal: string;
  color_secundario_1: string;
  color_secundario_2: string;
  color_texto: string;
};
export type Fraction = {
  total: number;
  transitadas: number;
  porcentaje: number;
  completo: boolean;
};
export type DirectionProgress = Fraction & { id: number; sentido: string };
export type BranchProgress = Fraction & {
  id: number;
  nombre: string;
  recorridos: DirectionProgress[];
};
export type LineProgress = Fraction & {
  linea: number;
  numero: string;
  ramales: BranchProgress[];
};
export type Line = {
  id: number;
  numero: string;
  nombre: string;
  colores: Palette | null;
  ramales_count: number;
  progreso: LineProgress;
};
export type StopOccurrence = {
  id: number;
  orden: number;
  transitada: boolean;
  parada: {
    id: number;
    nombre: string;
    direccion: string;
    barrio: string;
    coordenadas: [number, number];
  };
};
export type Route = {
  id: number;
  external_id: string;
  ramal: number;
  ramal_nombre: string;
  linea: number;
  linea_numero: string;
  sentido: string;
  desde: string;
  hasta: string;
  modalidad: string;
  jurisdiccion: string;
  camara: string;
  colores: Palette | null;
  geometria: MultiLineString | null;
  paradas: StopOccurrence[];
};
export type Level = {
  numero: number;
  nombre: string;
  puntos_minimos: number;
  siguiente: { numero: number; puntos_minimos: number } | null;
};
export type Profile = {
  id: number;
  username: string;
  nickname: string;
  avatar: string;
  puntos: number;
  nivel: Level;
  paradas: number;
  lineas_recorridas: number;
  ramales_completos: number;
  lineas_completas: number;
  ranking_global: number | null;
  ranking_semanal: number | null;
  ranking_amigos?: number | null;
  email?: string;
  public_profile?: boolean;
  theme?: Theme;
  logros: {
    logro__slug: string;
    logro__nombre: string;
    logro__descripcion: string;
  }[];
  lineas: LineProgress[];
};
export type PublicUser = Pick<
  Profile,
  "id" | "username" | "nickname" | "avatar"
> & { follow_id?: number | null };
export type RankingRow = PublicUser & {
  posicion: number;
  puntos: number;
  nivel: Level;
};
export type Achievement = {
  id: number;
  slug: string;
  nombre: string;
  descripcion: string;
  regla: string;
  objetivo: number;
  puntos: number;
  progreso: number;
  obtenido: boolean;
  fecha: string | null;
};
export type Trip = {
  id: number;
  recorrido: number;
  linea_numero: string;
  ramal_nombre: string;
  sentido: string;
  inicio_nombre: string;
  fin_nombre: string;
  fecha: string;
  resultado: {
    nuevas_paradas: number;
    puntos: number;
    logros: { slug: string; nombre: string }[];
    progreso: LineProgress;
  };
};
export type Page<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
export type Follow = { id: number; usuario: PublicUser };
