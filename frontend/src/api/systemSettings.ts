import { apiClient } from "@/api/client";
import type { RuntimeSettings } from "@/types";

export interface UpdateRuntimeSettingsPayload {
  default_target_score: number;
  default_max_rounds: number;
  default_style: string;
  use_mock_llm: "auto" | "true" | "false";
  openai_base_url: string;
  openai_model: string;
  openai_timeout_seconds: number;
  openai_max_retries: number;
}

export async function getRuntimeSettings(): Promise<RuntimeSettings> {
  const { data } = await apiClient.get<RuntimeSettings>("/system-settings/runtime");
  return data;
}

export async function updateRuntimeSettings(payload: UpdateRuntimeSettingsPayload): Promise<RuntimeSettings> {
  const { data } = await apiClient.put<RuntimeSettings>("/system-settings/runtime", payload);
  return data;
}
