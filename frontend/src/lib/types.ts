export type ProjectStatus =
  | "draft"
  | "story_generated"
  | "prompts_generated"
  | "images_generating"
  | "review"
  | "exported";

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
  page_id: number;
  image_path: string;
  prompt_used: string;
  provider: string;
  version_number: number;
  created_at: string;
}

export interface WsMessage {
  type: "image_progress" | "story_progress" | "prompts_progress" | "text_stream" | "text_done";
  page_number?: number;
  status?: "started" | "generating" | "completed" | "failed";
  image_path?: string;
  error?: string;
  chunk?: string;
  phase?: "story" | "prompts";
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
  story_system_prompt: string;
  image_system_prompt: string;
}
