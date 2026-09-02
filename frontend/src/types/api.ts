export type UUID = string;
export type DecimalString = string;
export type FurnitureType = "chair" | "dining_table" | "bookshelf";
export type ImageView = "front" | "back" | "left" | "right" | "top";
export type DimensionUnit = "mm" | "cm" | "m" | "in";
export type ComponentType = "panel" | "leg";
export type GeometryKind = "box" | "extruded_profile";
export type PlanStatus = "draft" | "finalized";
export type MaterialType = "wood" | "hardware";
export type MaterialUnit = "mm3" | "cm3" | "m3" | "board_ft" | "piece";

export interface Project {
  id: UUID;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface Furniture {
  id: UUID;
  project_id: UUID;
  name: string;
  furniture_type: FurnitureType | null;
  created_at: string;
  updated_at: string;
}

export interface FurnitureImage {
  id: UUID;
  furniture_id: UUID;
  view: ImageView;
  source: "upload" | "camera_capture";
  original_filename: string;
  content_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  pixel_width: number;
  pixel_height: number;
  created_at: string;
  updated_at: string;
}

export interface FurnitureClassification {
  id: UUID;
  furniture_id: UUID;
  predicted_type: FurnitureType;
  confidence: DecimalString | null;
  classifier_name: string;
  classifier_version: string | null;
  input_signature: string;
  created_at: string;
  updated_at: string;
}

export interface FurnitureDimensions {
  id: UUID;
  furniture_id: UUID;
  width_mm: DecimalString;
  height_mm: DecimalString;
  depth_mm: DecimalString;
  unit: DimensionUnit;
  source: "manual" | "ai_estimate";
  is_locked: boolean;
  locked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlanComponent {
  id: UUID;
  plan_id: UUID;
  component_name: string;
  component_type: ComponentType;
  width: DecimalString;
  height: DecimalString;
  depth: DecimalString | null;
  thickness: DecimalString | null;
  x: DecimalString;
  y: DecimalString;
  z: DecimalString;
  rotation: DecimalString;
  rotation_x: DecimalString;
  rotation_y: DecimalString;
  rotation_z: DecimalString;
  geometry_kind: GeometryKind;
  profile_points: Array<{ u: DecimalString; v: DecimalString }> | null;
  source_reconstruction_part_id: UUID | null;
  source_confidence: DecimalString | null;
  source_views: ImageView[];
  quantity: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export type PlanComponentPayload = Pick<
  PlanComponent,
  | "component_name"
  | "component_type"
  | "width"
  | "height"
  | "depth"
  | "thickness"
  | "x"
  | "y"
  | "z"
  | "rotation"
  | "rotation_x"
  | "rotation_y"
  | "rotation_z"
  | "geometry_kind"
  | "profile_points"
  | "quantity"
  | "sort_order"
>;

export interface FurniturePlan {
  id: UUID;
  furniture_id: UUID;
  revision: number;
  status: PlanStatus;
  furniture_type: FurnitureType;
  source_reconstruction_id: UUID | null;
  components: PlanComponent[];
  created_at: string;
  updated_at: string;
}

export interface Vector3D {
  x: DecimalString;
  y: DecimalString;
  z: DecimalString;
}

export interface GeometryComponent {
  source_component_id: UUID;
  component_name: string;
  component_type: ComponentType;
  dimensions: { width: DecimalString; height: DecimalString; depth: DecimalString };
  min_corner: Vector3D;
  center: Vector3D;
  depth_source: "component_depth" | "thickness";
  rotation_degrees: DecimalString;
  rotation: Vector3D;
  geometry_kind: GeometryKind;
  profile_points: Array<{ u: DecimalString; v: DecimalString }> | null;
  quantity: number;
  sort_order: number;
}

export interface ReconstructionPart {
  id: UUID;
  reconstruction_id: UUID;
  component_name: string;
  component_type: ComponentType;
  geometry_kind: GeometryKind;
  profile_points: Array<{ u: DecimalString; v: DecimalString }> | null;
  width: DecimalString;
  height: DecimalString;
  depth: DecimalString;
  x: DecimalString;
  y: DecimalString;
  z: DecimalString;
  rotation_x: DecimalString;
  rotation_y: DecimalString;
  rotation_z: DecimalString;
  quantity: number;
  sort_order: number;
  confidence: DecimalString | null;
  source_views: ImageView[];
  created_at: string;
  updated_at: string;
}

export interface FurnitureReconstruction {
  id: UUID;
  furniture_id: UUID;
  input_signature: string;
  furniture_type: FurnitureType;
  provider_name: string;
  provider_version: string | null;
  confidence: DecimalString | null;
  warnings: string[];
  parts: ReconstructionPart[];
  created_at: string;
  updated_at: string;
}

export interface PlanGeometry {
  plan_id: UUID;
  furniture_id: UUID;
  revision: number;
  furniture_type: FurnitureType;
  unit: "mm";
  components: GeometryComponent[];
}

export interface Material {
  id: UUID;
  material_name: string;
  material_type: MaterialType;
  unit: MaterialUnit;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LaborRate {
  id: UUID;
  rate_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialQuantity {
  plan_id: UUID;
  total_volume_mm3: DecimalString;
  unit: "mm3";
  components: Array<{
    source_component_id: UUID;
    component_name: string;
    total_volume_mm3: DecimalString;
    quantity: number;
  }>;
}

export interface HardwareQuantity {
  plan_id: UUID;
  item_name: "Wood screw";
  total_connections: number;
  total_quantity: number;
  unit: "piece";
}

export interface LaborQuantity {
  plan_id: UUID;
  labor_hours: DecimalString;
  unit: "hour";
  rules: Array<{
    rule_code: string;
    unit_count: number;
    hours_per_unit: DecimalString;
    labor_hours: DecimalString;
    rule_description: string;
  }>;
}

export interface MaterialCost {
  material_id: UUID;
  material_name: string;
  price_per_unit: DecimalString;
  price_unit: MaterialUnit;
  total_quantity_in_price_unit: DecimalString;
  total_cost: DecimalString;
}

export interface HardwareCost {
  material_id: UUID;
  material_name: string;
  price_per_piece: DecimalString;
  quantity: number;
  total_cost: DecimalString;
}

export interface LaborCost {
  labor_rate_id: UUID;
  labor_rate_name: string;
  labor_hours: DecimalString;
  rate_per_hour: DecimalString;
  total_cost: DecimalString;
}

export interface CompleteCost {
  material: MaterialCost;
  hardware: HardwareCost;
  labor: LaborCost;
  total_cost: DecimalString;
}

export interface CostSelection {
  material_id: UUID;
  hardware_material_id: UUID;
  labor_rate_id: UUID;
}

export interface Quotation {
  id: UUID;
  quotation_number: string;
  project_id: UUID;
  furniture_id: UUID;
  plan_id: UUID;
  plan_revision: number;
  furniture_type: FurnitureType;
  wood_material_name: string;
  wood_price_per_unit: DecimalString;
  wood_price_unit: MaterialUnit;
  wood_quantity: DecimalString;
  wood_material_cost: DecimalString;
  hardware_material_name: string;
  hardware_price_per_piece: DecimalString;
  hardware_quantity: number;
  hardware_cost: DecimalString;
  labor_rate_name: string;
  labor_rate_per_hour: DecimalString;
  labor_hours: DecimalString;
  labor_cost: DecimalString;
  total_cost: DecimalString;
  created_at: string;
  updated_at: string;
}
