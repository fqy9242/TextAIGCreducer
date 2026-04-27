<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { cancelTask } from "@/api/tasks";
import { getRuntimeSettings } from "@/api/systemSettings";
import { useTaskStore } from "@/stores/task";
import ScoreTag from "@/components/ScoreTag.vue";
import type { RuntimeSettings, TaskResult } from "@/types";

const router = useRouter();
const taskStore = useTaskStore();
const runtimeSettings = ref<RuntimeSettings | null>(null);
const loadingSettings = ref(false);
const submitting = ref(false);
const refreshingTasks = ref(false);
const latestTaskId = ref("");
const selectedTaskId = ref("");
const refreshTimer = ref<number | null>(null);
const knownStatuses = new Map<string, string>();

const form = reactive({
  input_text: "",
  target_score: 20,
  max_rounds: 3,
  style: "deai_external",
});

const styleOptions = computed(() => {
  if (runtimeSettings.value?.available_styles?.length) {
    return runtimeSettings.value.available_styles;
  }
  return [form.style];
});
const trackedTasks = computed(() => taskStore.trackedTasks);
const selectedTask = computed(() => {
  if (trackedTasks.value.length === 0) return null;
  return trackedTasks.value.find((task) => task.id === selectedTaskId.value) ?? trackedTasks.value[0];
});
const queuedCount = computed(() => trackedTasks.value.filter((task) => task.status === "queued").length);
const runningCount = computed(() => trackedTasks.value.filter((task) => task.status === "running").length);
const finishedCount = computed(() => trackedTasks.value.filter((task) => taskStore.isFinalStatus(task.status)).length);

function statusTagType(status: string): "info" | "warning" | "success" | "danger" {
  if (status === "success") return "success";
  if (status === "not_met" || status === "queued") return "warning";
  if (status === "failed" || status === "cancelled") return "danger";
  return "info";
}

function formatElapsed(seconds: number | null | undefined): string {
  if (seconds == null) return "--";
  const total = Math.max(0, Math.floor(seconds));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) {
    return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s
      .toString()
      .padStart(2, "0")}`;
  }
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatShortTaskId(taskId: string): string {
  if (!taskId) return "";
  return taskId.length <= 8 ? taskId : `...${taskId.slice(-8)}`;
}

function ensureSelection(): void {
  if (trackedTasks.value.length === 0) {
    selectedTaskId.value = "";
    return;
  }
  if (!trackedTasks.value.some((task) => task.id === selectedTaskId.value)) {
    selectedTaskId.value = trackedTasks.value[0].id;
  }
}

function selectTask(taskId: string): void {
  selectedTaskId.value = taskId;
}

function taskRowClassName(payload: { row: TaskResult }): string {
  return payload.row.id === selectedTaskId.value ? "is-selected-row" : "";
}

function onTaskRowClick(row: TaskResult): void {
  selectTask(row.id);
}

function notifyFinishedTasks(): void {
  for (const task of trackedTasks.value) {
    const previousStatus = knownStatuses.get(task.id);
    if (previousStatus && previousStatus !== task.status && taskStore.isFinalStatus(task.status)) {
      if (task.status === "success") {
        ElMessage.success(`任务 ${task.id.slice(0, 8)} 达标完成`);
      } else if (task.status === "not_met") {
        ElMessage.warning(`任务 ${task.id.slice(0, 8)} 已达到最大轮次`);
      } else if (task.status === "cancelled") {
        ElMessage.warning(`任务 ${task.id.slice(0, 8)} 已取消`);
      } else if (task.status === "failed") {
        ElMessage.error(task.error_message ?? `任务 ${task.id.slice(0, 8)} 执行失败`);
      }
    }
    knownStatuses.set(task.id, task.status);
  }
}

async function loadRuntimeConfig() {
  loadingSettings.value = true;
  try {
    const settings = await getRuntimeSettings();
    runtimeSettings.value = settings;
    form.target_score = settings.default_target_score;
    form.max_rounds = settings.default_max_rounds;
    form.style = settings.default_style;
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载系统设置失败");
  } finally {
    loadingSettings.value = false;
  }
}

async function refreshWorkspaceTasks(showError = false) {
  if (refreshingTasks.value) return;
  refreshingTasks.value = true;
  try {
    await taskStore.refreshTrackedTasks();
    ensureSelection();
    notifyFinishedTasks();
  } catch (error: any) {
    if (showError) {
      ElMessage.error(error?.response?.data?.detail ?? "刷新任务状态失败");
    }
  } finally {
    refreshingTasks.value = false;
  }
}

async function submitTask() {
  if (form.input_text.trim().length < 20) {
    ElMessage.warning("文本至少需要 20 个字符");
    return;
  }

  submitting.value = true;
  try {
    const task = await taskStore.submitTask({
      input_text: form.input_text,
      target_score: form.target_score,
      max_rounds: form.max_rounds,
      style: form.style,
    });
    latestTaskId.value = task.id;
    selectedTaskId.value = task.id;
    knownStatuses.set(task.id, task.status);
    ElMessage.success("任务已提交，已加入并发执行队列");
    await refreshWorkspaceTasks();
  } catch (error: any) {
    const message = error?.response?.data?.detail ?? "任务提交失败";
    ElMessage.error(String(message));
  } finally {
    submitting.value = false;
  }
}

function openTaskDetail() {
  const taskId = selectedTask.value?.id || latestTaskId.value;
  if (!taskId) return;
  router.push({ name: "task-detail", params: { id: taskId } });
}

function openSpecificTaskDetail(taskId: string) {
  if (!taskId) return;
  router.push({ name: "task-detail", params: { id: taskId } });
}

async function cancelTrackedTask(task: TaskResult) {
  try {
    await ElMessageBox.confirm("确定要终止该任务吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    await cancelTask(task.id);
    ElMessage.success("任务已成功终止");
    await taskStore.fetchTask(task.id, { setCurrent: false, track: true });
    ensureSelection();
    notifyFinishedTasks();
  } catch (error: any) {
    if (error !== "cancel") {
      const message = error?.response?.data?.detail ?? error?.message ?? "终止任务失败";
      ElMessage.error(String(message));
    }
  }
}

function clearFinishedTasks() {
  taskStore.clearFinishedTrackedTasks();
  ensureSelection();
}

onMounted(async () => {
  await loadRuntimeConfig();
  await refreshWorkspaceTasks();
  ensureSelection();
  refreshTimer.value = window.setInterval(() => {
    void refreshWorkspaceTasks();
  }, 2000);
});

onUnmounted(() => {
  if (refreshTimer.value != null) {
    window.clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
});
</script>

<template>
  <section>
    <div class="page-actions">
      <div class="actions">
        <el-button @click="refreshWorkspaceTasks(true)" :loading="refreshingTasks">刷新状态</el-button>
        <el-button @click="clearFinishedTasks" :disabled="finishedCount === 0">清理已完成</el-button>
        <el-button type="primary" :disabled="!selectedTask && !latestTaskId" @click="openTaskDetail">查看任务详情</el-button>
      </div>
    </div>

    <div class="kpi-row" v-loading="loadingSettings">
      <div class="kpi-card">
        <span>策略模式</span>
        <strong>{{ form.style }}</strong>
      </div>
      <div class="kpi-card">
        <span>目标阈值</span>
        <strong>{{ form.target_score }}%</strong>
      </div>
      <div class="kpi-card">
        <span>排队 / 执行中</span>
        <strong>{{ queuedCount }} / {{ runningCount }}</strong>
      </div>
      <div class="kpi-card">
        <span>已完成追踪</span>
        <strong>{{ finishedCount }}</strong>
      </div>
    </div>

    <div class="grid-two">
      <article class="app-card panel">
        <el-form label-position="top" v-loading="loadingSettings">
          <el-form-item label="原始文本">
            <el-input
              v-model="form.input_text"
              type="textarea"
              :rows="14"
              placeholder="输入待改写文本"
              maxlength="20000"
              show-word-limit
            />
          </el-form-item>
          <div class="params">
            <el-form-item label="目标AIGC率(%)">
              <el-input-number v-model="form.target_score" :min="1" :max="100" />
            </el-form-item>
            <el-form-item label="最大轮次">
              <el-input-number v-model="form.max_rounds" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="策略">
              <el-select v-model="form.style">
                <el-option v-for="item in styleOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </div>
          <el-button type="primary" :loading="submitting" class="submit-btn" @click="submitTask">启动智能改写</el-button>
        </el-form>
      </article>

      <article class="app-card panel side-panel">
        <div class="side-head">
          <h3>实时任务看板</h3>
          <span>{{ trackedTasks.length }} 个追踪任务</span>
        </div>
        <el-empty v-if="trackedTasks.length === 0" description="尚未提交任务" />
        <template v-else>
          <el-table
            :data="trackedTasks"
            size="small"
            max-height="260"
            row-key="id"
            :row-class-name="taskRowClassName"
            @row-click="onTaskRowClick"
          >
            <el-table-column prop="id" label="任务ID" width="110">
              <template #default="{ row }">
                <span class="mono-id" :title="row.id">{{ formatShortTaskId(row.id) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag size="small" :type="statusTagType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="分数" width="100">
              <template #default="{ row }">
                <ScoreTag :score="row.best_score" />
              </template>
            </el-table-column>
            <el-table-column label="时长" width="90">
              <template #default="{ row }">
                {{ formatElapsed(row.elapsed_seconds) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="openSpecificTaskDetail(row.id)">详情</el-button>
                <el-button
                  v-if="['queued', 'running'].includes(row.status)"
                  link
                  type="danger"
                  @click.stop="cancelTrackedTask(row)"
                >
                  终止
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-descriptions v-if="selectedTask" :column="1" border class="selected-task">
            <el-descriptions-item label="任务ID">
              <span class="mono-id">{{ selectedTask.id }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">{{ selectedTask.status }}</el-descriptions-item>
            <el-descriptions-item label="最佳分数">
              <ScoreTag :score="selectedTask.best_score" />
            </el-descriptions-item>
            <el-descriptions-item label="已用轮次">
              {{ selectedTask.rounds_used }} / {{ selectedTask.max_rounds }}
            </el-descriptions-item>
            <el-descriptions-item label="已执行时间">
              {{ formatElapsed(selectedTask.elapsed_seconds) }}
            </el-descriptions-item>
          </el-descriptions>
          <h4>最佳文本预览</h4>
          <el-input
            type="textarea"
            :rows="12"
            :model-value="selectedTask?.best_text ?? ''"
            readonly
          />
        </template>
      </article>
    </div>
  </section>
</template>

<style scoped>
.panel {
  padding: 18px;
}

.page-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.actions {
  display: flex;
  gap: 8px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 14px;
}

.kpi-card {
  border-radius: 10px;
  border: 1px solid #d8e4f2;
  background: linear-gradient(180deg, #fff 0%, #f7fbff 100%);
  padding: 12px;
}

.kpi-card span {
  color: #657d99;
  font-size: 12px;
}

.kpi-card strong {
  display: block;
  margin-top: 3px;
  font-size: 16px;
  color: #1d3656;
  font-weight: 700;
}

.params {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.submit-btn {
  min-width: 130px;
}

.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.side-head h3 {
  margin: 0;
}

.side-head span {
  color: #657d99;
  font-size: 12px;
}

.side-panel h4 {
  margin: 16px 0 8px;
}

.selected-task {
  margin-top: 14px;
}

.mono-id {
  font-family: Consolas, "Courier New", monospace;
  font-size: 12px;
}

:deep(.el-table .is-selected-row > td) {
  background: #eef6ff !important;
}

@media (max-width: 900px) {
  .page-actions {
    justify-content: flex-start;
  }

  .actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .kpi-row {
    grid-template-columns: 1fr;
  }

  .params {
    grid-template-columns: 1fr;
  }

  :deep(.el-table__body-wrapper) {
    overflow-x: auto;
  }
}
</style>
