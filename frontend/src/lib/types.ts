export type ProjectStatus =
  | "draft"
  | "ref_pic_generating"
  | "ref_pic_review"
  | "story_generating"
  | "story_generated"
  | "prompts_generating"
  | "prompts_generated"
  | "images_generating"
  | "review"
  | "exported";

export type FulfillmentStatus =
  | "oczekuje"
  | "w_drukarni"
  | "wyslane"
  | "doreczone";

export const FULFILLMENT_LABELS: Record<FulfillmentStatus, string> = {
  oczekuje: "Oczekuje",
  w_drukarni: "W drukarni",
  wyslane: "Wysłane",
  doreczone: "Doręczone",
};

export const FULFILLMENT_ORDER: FulfillmentStatus[] = [
  "oczekuje",
  "w_drukarni",
  "wyslane",
  "doreczone",
];

export type ExportFormat = "zip" | "excel" | "txt";

export interface Project {
  id: number;
  child_name: string;
  child_age: number;
  child_gender: string;
  hair_color: string;
  hair_style: string;
  skin_tone: string;
  eye_color: string;
  outfit_description: string;
  story_type: string;
  hobby: string;
  moral: string;
  raw_story: string | null;
  raw_image_prompts: string | null;
  llm_provider: string;
  image_provider: string;
  reference_image_prompt: string | null;
  reference_image_path: string | null;
  reference_image_version: number;
  story_prompt_id: number | null;
  image_prompt_id: number | null;
  fulfillment_status: FulfillmentStatus;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateInput {
  child_name: string;
  child_age: number;
  child_gender: string;
  hair_color: string;
  hair_style: string;
  skin_tone: string;
  eye_color: string;
  outfit_description: string;
  story_type: string;
  hobby: string;
  moral: string;
  llm_provider?: string;
  image_provider?: string;
  story_prompt_id?: number | null;
  image_prompt_id?: number | null;
}

export interface ProjectUpdateInput {
  child_name?: string;
  child_age?: number;
  child_gender?: string;
  hair_color?: string;
  hair_style?: string;
  skin_tone?: string;
  eye_color?: string;
  outfit_description?: string;
  story_type?: string;
  hobby?: string;
  moral?: string;
  llm_provider?: string;
  image_provider?: string;
  story_prompt_id?: number | null;
  image_prompt_id?: number | null;
  fulfillment_status?: FulfillmentStatus;
}

export type PageType = "cover" | "story" | "back";

export interface Page {
  id: number;
  project_id: number;
  page_number: number;
  page_type: PageType;
  text: string | null;
  image_prompt: string | null;
  current_image_path: string | null;
  reference_image_path: string | null;
  version: number;
}

export interface ImageVersion {
  id: number;
  page_id: number | null;
  project_id: number | null;
  kind: "page" | "reference";
  image_path: string;
  prompt_used: string;
  provider: string;
  version_number: number;
  created_at: string;
}

export type PromptKind = "story" | "image";

export interface Prompt {
  id: number;
  kind: PromptKind;
  title: string;
  content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface PromptInput {
  kind: PromptKind;
  title: string;
  content: string;
}

export interface WsMessage {
  type:
    | "image_progress"
    | "story_progress"
    | "prompts_progress"
    | "text_stream"
    | "text_done"
    | "project_status";
  page_number?: number;
  page_id?: number;
  status?: "started" | "generating" | "completed" | "failed" | ProjectStatus;
  image_path?: string;
  version?: number;
  error?: string;
  chunk?: string;
  phase?: "story" | "prompts" | "reference";
}

export interface AppSettings {
  anthropic_api_key: string;
  openai_api_key: string;
  nano_banana_api_key: string;
  google_api_key: string;
  default_llm_provider: string;
  default_image_provider: string;
  image_aspect_ratio: string;
  image_size: string;
}
