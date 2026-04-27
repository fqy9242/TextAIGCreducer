import { ref } from "vue";
import { defineStore } from "pinia";
import * as taskApi from "@/api/tasks";
import type { CreateTaskPayload } from "@/api/tasks";
import type { TaskListResponse, TaskResult } from "@/types";

const FINAL_STATUSES = new Set(["success", "not_met", "failed", "error", "cancelled"]);

interface FetchTaskOptions {
  setCurrent?: boolean;
  track?: boolean;
}

export const useTaskStore = defineStore("task", () => {
  const currentTask = ref<TaskResult | null>(null);
  const taskList = ref<TaskListResponse | null>(null);
  const trackedTasks = ref<TaskResult[]>([]);
  const loading = ref(false);

  function isFinalStatus(status: string): boolean {
    return FINAL_STATUSES.has(status);
  }

  function cloneTask(task: TaskResult): TaskResult {
    return {
      ...task,
      iterations: [...task.iterations],
      logs: [...task.logs],
    };
  }

  function setCurrentTask(task: TaskResult | null): void {
    currentTask.value = task ? cloneTask(task) : null;
  }

  function rememberTrackedTask(task: TaskResult): TaskResult {
    const normalized = cloneTask(task);
    const index = trackedTasks.value.findIndex((item) => item.id === normalized.id);
    if (index >= 0) {
      trackedTasks.value[index] = normalized;
    } else {
      trackedTasks.value.unshift(normalized);
    }
    trackedTasks.value.sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
    return normalized;
  }

  function clearFinishedTrackedTasks(): void {
    trackedTasks.value = trackedTasks.value.filter((task) => !isFinalStatus(task.status));
  }

  function bumpElapsedSeconds(task: { id: string; status: string; elapsed_seconds: number | null }): void {
    if (task.status === "running" && task.elapsed_seconds != null) {
      task.elapsed_seconds += 1;
    }
  }

  // Auto-increment elapsed time for active tasks shown in different views.
  setInterval(() => {
    const seenTaskIds = new Set<string>();

    if (currentTask.value) {
      bumpElapsedSeconds(currentTask.value);
      seenTaskIds.add(currentTask.value.id);
    }

    if (taskList.value?.items) {
      for (const task of taskList.value.items) {
        if (seenTaskIds.has(task.id)) {
          continue;
        }
        bumpElapsedSeconds(task);
        seenTaskIds.add(task.id);
      }
    }

    for (const task of trackedTasks.value) {
      if (seenTaskIds.has(task.id)) {
        continue;
      }
      bumpElapsedSeconds(task);
      seenTaskIds.add(task.id);
    }
  }, 1000);

  async function submitTask(payload: CreateTaskPayload): Promise<TaskResult> {
    loading.value = true;
    try {
      const task = await taskApi.createTask(payload);
      setCurrentTask(task);
      rememberTrackedTask(task);
      return task;
    } finally {
      loading.value = false;
    }
  }

  async function fetchTask(taskId: string, options: FetchTaskOptions = {}): Promise<TaskResult> {
    const task = await taskApi.getTask(taskId);
    if (options.setCurrent !== false) {
      setCurrentTask(task);
    }
    if (options.track) {
      rememberTrackedTask(task);
    }
    return task;
  }

  async function pollTask(
    taskId: string,
    maxAttempts = 50,
    intervalMs = 1000,
    options: FetchTaskOptions = {},
  ): Promise<TaskResult> {
    let latest = await fetchTask(taskId, options);
    for (let i = 0; i < maxAttempts; i += 1) {
      if (isFinalStatus(latest.status)) {
        return latest;
      }
      await new Promise((resolve) => {
        window.setTimeout(resolve, intervalMs);
      });
      latest = await fetchTask(taskId, options);
    }
    return latest;
  }

  async function refreshTrackedTasks(): Promise<TaskResult[]> {
    const pendingTaskIds = new Set(
      trackedTasks.value.filter((task) => !isFinalStatus(task.status)).map((task) => task.id),
    );
    const recentTasks = await taskApi.listTasks(1, 100);
    for (const task of recentTasks.items) {
      if (task.status === "queued" || task.status === "running") {
        pendingTaskIds.add(task.id);
      }
    }

    if (pendingTaskIds.size === 0) {
      return trackedTasks.value;
    }

    await Promise.all(
      Array.from(pendingTaskIds).map((taskId) =>
        fetchTask(taskId, {
          setCurrent: false,
          track: true,
        }),
      ),
    );
    return trackedTasks.value;
  }

  async function loadTaskList(page = 1, pageSize = 10): Promise<TaskListResponse> {
    const result = await taskApi.listTasks(page, pageSize);
    taskList.value = result;
    return result;
  }

  return {
    currentTask,
    taskList,
    trackedTasks,
    loading,
    isFinalStatus,
    rememberTrackedTask,
    clearFinishedTrackedTasks,
    submitTask,
    fetchTask,
    pollTask,
    refreshTrackedTasks,
    loadTaskList,
  };
});
