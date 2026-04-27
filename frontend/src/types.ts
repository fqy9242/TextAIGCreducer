export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface TaskIteration {
  round: number;
  prompt_version: string;
  rewritten_text: string;
  detector_score: number;
  detector_label: "ai_like" | "human_like" | "uncertain";
  llm_mode?: string | null;
  latency_ms: number;
  created_at: string;
}

export interface TaskLog {
  level: "debug" | "info" | "warning" | "error" | string;
  stage: string;
  message: string;
  detail: Record<string, unknown>;
  created_at: string;
}

export interface TaskResult {
  id: string;
  status: "queued" | "running" | "success" | "not_met" | "failed" | "cancelled";
  input_text: string;
  best_text: string | null;
  best_score: number | null;
  met_target: boolean;
  target_score: number;
  max_rounds: number;
  rounds_used: number;
  style: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  elapsed_seconds: number | null;
  iterations: TaskIteration[];
  logs: TaskLog[];
}

export interface TaskListItem {
  id: string;
  status: string;
  target_score: number;
  best_score: number | null;
  met_target: boolean;
  rounds_used: number;
  style: string;
  created_at: string;
  completed_at: string | null;
  elapsed_seconds: number | null;
}

export interface TaskListResponse {
  items: TaskListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserOut {
  id: number;
  username: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

export interface PromptMeta {
  group: string;
  name: string;
  version: string;
  variables: string[];
  file_path: string;
}

export interface PromptDetail extends PromptMeta {
  system: string;
  human: string;
  instruction: string;
}

export interface RuntimeSettings {
  default_target_score: number;
  default_max_rounds: number;
  default_style: string;
  openai_base_url: string;
  openai_model: string;
  openai_timeout_seconds: number;
  openai_max_retries: number;
  detector_model: string;
  available_styles: string[];
  has_openai_api_key: boolean;
}
