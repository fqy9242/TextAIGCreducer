import { apiClient } from "@/api/client";
import type { TaskListResponse, TaskResult } from "@/types";

export interface CreateTaskPayload {
  input_text: string;
  target_score: number;
  max_rounds: number;
  style: string;
}

export async function createTask(payload: CreateTaskPayload): Promise<TaskResult> {
  const { data } = await apiClient.post<TaskResult>("/tasks", payload);
  return data;
}

export async function getTask(taskId: string): Promise<TaskResult> {
  const { data } = await apiClient.get<TaskResult>(`/tasks/${taskId}`);
  return data;
}

export async function listTasks(page = 1, pageSize = 10): Promise<TaskListResponse> {
  const { data } = await apiClient.get<TaskListResponse>("/tasks", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function exportTask(taskId: string): Promise<string> {
  const { data } = await apiClient.get<string>(`/tasks/${taskId}/export`, {
    responseType: "text",
  });
  return data;
}
