export interface Fermentable {
  name: string;
  amount_kg: number;
  color_ebc: number;
  ppg: number;
}

export interface Hop {
  name: string;
  amount_g: number;
  alpha_pct: number;
  time_min: number;
  use: "boil" | "whirlpool" | "dry-hop";
}

export interface Yeast {
  name: string;
  attenuation_pct: number;
  min_temp_c: number;
  max_temp_c: number;
}

export interface CalculatedStats {
  og: number;
  fg: number;
  abv: number;
  ibu: number;
  srm: number;
}

export interface Recipe {
  id: string;
  name: string;
  style: string;
  batch_size_liters: number;
  fermentables: Fermentable[];
  hops: Hop[];
  yeast: Yeast;
}

export interface RecipeWithStats extends Recipe {
  calculated: CalculatedStats;
}

export interface RecipePatch {
  name?: string;
  style?: string;
  batch_size_liters?: number;
  fermentables?: Fermentable[];
  hops?: Hop[];
  yeast?: Yeast;
}

export interface BrewNotes {
  content: string;
}

export interface Style {
  name: string;
  category: string;
  og_min: number;
  og_max: number;
  fg_min: number;
  fg_max: number;
  ibu_min: number;
  ibu_max: number;
  srm_min: number;
  srm_max: number;
  abv_min: number;
  abv_max: number;
  description: string;
}

export interface SensoryProfile {
  aroma: string;
  flavor: string;
  mouthfeel: string;
  appearance: string;
}
