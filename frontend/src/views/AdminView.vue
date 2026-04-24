<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { createUser, listUsers, updateUserRole } from "@/api/users";
import { getPromptDetail, listPromptMetadata, reloadPrompts, updatePrompt } from "@/api/prompts";
import { getRuntimeSettings, updateRuntimeSettings } from "@/api/systemSettings";
import type { PromptMeta, RuntimeSettings, UserOut } from "@/types";

const users = ref<UserOut[]>([]);
const prompts = ref<PromptMeta[]>([]);
const loadingUsers = ref(false);
const loadingPrompts = ref(false);
const loadingPromptDetail = ref(false);
const loadingSystemSettings = ref(false);
const savingPrompt = ref(false);
const savingSystemSettings = ref(false);
const forbidden = ref(false);
const selectedPromptKey = ref("");
const runtimeStyleOptions = ref<string[]>([]);

const createForm = reactive({
  username: "",
  password: "",
  role: "operator",
});

const promptForm = reactive({
  group: "",
  name: "",
  version: "",
  variablesText: "",
  system: "",
  human: "",
  instruction: "",
});

const systemForm = reactive({
  default_target_score: 20,
  default_max_rounds: 3,
  default_style: "deai_external",
  use_mock_llm: "auto" as RuntimeSettings["use_mock_llm"],
  openai_base_url: "https://api.openai.com/v1",
  openai_model: "gpt-4o-mini",
  openai_timeout_seconds: 60,
  openai_max_retries: 0,
  has_openai_api_key: false,
  effective_llm_mode: "mock" as RuntimeSettings["effective_llm_mode"],
});

const promptLabel = computed(() => {
  if (!promptForm.group || !promptForm.name) return "";
  return `${promptForm.group}.${promptForm.name}`;
});
const llmModeTagType = computed(() => (systemForm.effective_llm_mode === "real" ? "success" : "info"));

function toPromptKey(group: string, name: string): string {
  return `${group}:${name}`;
}

function clearPromptForm() {
  promptForm.group = "";
  promptForm.name = "";
  promptForm.version = "";
  promptForm.variablesText = "";
  promptForm.system = "";
  promptForm.human = "";
  promptForm.instruction = "";
}

function parseVariables(value: string): string[] {
  return value
    .split(/[\n,，]/)
    .map((item) => item.trim())
    .filter((item, index, arr) => item.length > 0 && arr.indexOf(item) === index);
}

function applyRuntimeSettings(value: RuntimeSettings) {
  systemForm.default_target_score = value.default_target_score;
  systemForm.default_max_rounds = value.default_max_rounds;
  systemForm.default_style = value.default_style;
  systemForm.use_mock_llm = value.use_mock_llm;
  systemForm.openai_base_url = value.openai_base_url;
  systemForm.openai_model = value.openai_model;
  systemForm.openai_timeout_seconds = value.openai_timeout_seconds;
  systemForm.openai_max_retries = value.openai_max_retries;
  systemForm.has_openai_api_key = value.has_openai_api_key;
  systemForm.effective_llm_mode = value.effective_llm_mode;
  runtimeStyleOptions.value = value.available_styles;
}

async function loadUsers() {
  loadingUsers.value = true;
  try {
    users.value = await listUsers();
    forbidden.value = false;
  } catch (error: any) {
    if (error?.response?.status === 403) {
      forbidden.value = true;
      ElMessage.warning("当前账号无管理员权限");
    } else {
      ElMessage.error(error?.response?.data?.detail ?? "加载用户列表失败");
    }
  } finally {
    loadingUsers.value = false;
  }
}

async function loadPromptDetail(group: string, name: string) {
  loadingPromptDetail.value = true;
  try {
    const detail = await getPromptDetail(group, name);
    promptForm.group = detail.group;
    promptForm.name = detail.name;
    promptForm.version = detail.version;
    promptForm.variablesText = detail.variables.join(", ");
    promptForm.system = detail.system ?? "";
    promptForm.human = detail.human ?? "";
    promptForm.instruction = detail.instruction ?? "";
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载 Prompt 详情失败");
  } finally {
    loadingPromptDetail.value = false;
  }
}

async function loadPrompts() {
  loadingPrompts.value = true;
  try {
    const previousKey = selectedPromptKey.value;
    prompts.value = await listPromptMetadata();
    if (prompts.value.length === 0) {
      selectedPromptKey.value = "";
      clearPromptForm();
      return;
    }

    const selected =
      prompts.value.find((item) => toPromptKey(item.group, item.name) === previousKey) ?? prompts.value[0];
    selectedPromptKey.value = toPromptKey(selected.group, selected.name);
    await loadPromptDetail(selected.group, selected.name);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载 Prompt 元数据失败");
  } finally {
    loadingPrompts.value = false;
  }
}

async function loadSystemSettings() {
  loadingSystemSettings.value = true;
  try {
    const settings = await getRuntimeSettings();
    applyRuntimeSettings(settings);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "加载系统设置失败");
  } finally {
    loadingSystemSettings.value = false;
  }
}

async function createNewUser() {
  if (!createForm.username || !createForm.password) {
    ElMessage.warning("请填写用户名和密码");
    return;
  }
  try {
    await createUser(createForm.username, createForm.password, createForm.role);
    ElMessage.success("用户创建成功");
    createForm.username = "";
    createForm.password = "";
    createForm.role = "operator";
    await loadUsers();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "创建用户失败");
  }
}

async function changeRole(userId: number, role: string) {
  try {
    await updateUserRole(userId, role);
    ElMessage.success("角色更新成功");
    await loadUsers();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "角色更新失败");
  }
}

async function reloadPromptDefinitions() {
  try {
    await reloadPrompts();
    ElMessage.success("Prompt 已热重载");
    await Promise.all([loadPrompts(), loadSystemSettings()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "Prompt 重载失败");
  }
}

async function selectPrompt(row: PromptMeta) {
  selectedPromptKey.value = toPromptKey(row.group, row.name);
  await loadPromptDetail(row.group, row.name);
}

function promptRowClassName({ row }: { row: PromptMeta }): string {
  return toPromptKey(row.group, row.name) === selectedPromptKey.value ? "is-selected-row" : "";
}

async function reloadCurrentPrompt() {
  if (!promptForm.group || !promptForm.name) return;
  await loadPromptDetail(promptForm.group, promptForm.name);
}

async function savePromptChanges() {
  if (!promptForm.group || !promptForm.name) {
    ElMessage.warning("请先选择一个 Prompt");
    return;
  }

  if (!promptForm.version.trim()) {
    ElMessage.warning("版本号不能为空");
    return;
  }

  if (promptForm.group === "rewrite") {
    if (!promptForm.system.trim() || !promptForm.human.trim()) {
      ElMessage.warning("rewrite Prompt 必须包含 system 和 human");
      return;
    }
  } else if (!promptForm.instruction.trim()) {
    ElMessage.warning("instruction 不能为空");
    return;
  }

  savingPrompt.value = true;
  try {
    await updatePrompt(promptForm.group, promptForm.name, {
      version: promptForm.version.trim(),
      variables: parseVariables(promptForm.variablesText),
      system: promptForm.system,
      human: promptForm.human,
      instruction: promptForm.instruction,
    });
    ElMessage.success("Prompt 保存成功");
    await Promise.all([loadPrompts(), loadSystemSettings()]);
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "Prompt 保存失败");
  } finally {
    savingPrompt.value = false;
  }
}

async function saveSystemSettings() {
  if (!systemForm.default_style.trim()) {
    ElMessage.warning("默认策略不能为空");
    return;
  }
  if (!systemForm.openai_base_url.trim() || !systemForm.openai_model.trim()) {
    ElMessage.warning("Base URL 和模型名不能为空");
    return;
  }

  savingSystemSettings.value = true;
  try {
    const settings = await updateRuntimeSettings({
      default_target_score: systemForm.default_target_score,
      default_max_rounds: systemForm.default_max_rounds,
      default_style: systemForm.default_style,
      use_mock_llm: systemForm.use_mock_llm,
      openai_base_url: systemForm.openai_base_url.trim(),
      openai_model: systemForm.openai_model.trim(),
      openai_timeout_seconds: systemForm.openai_timeout_seconds,
      openai_max_retries: systemForm.openai_max_retries,
    });
    applyRuntimeSettings(settings);
    ElMessage.success("系统设置已保存");
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail ?? "系统设置保存失败");
  } finally {
    savingSystemSettings.value = false;
  }
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadPrompts(), loadSystemSettings()]);
});
</script>

<template>
  <section>
    <div class="page-actions">
      <el-button @click="reloadPromptDefinitions" :loading="loadingPrompts || loadingPromptDetail">
        重载 Prompt
      </el-button>
    </div>

    <el-alert
      v-if="forbidden"
      title="当前账号缺少管理员权限，部分功能不可用。"
      type="warning"
      show-icon
      :closable="false"
      class="alert"
    />

    <article class="app-card panel settings-panel" v-loading="loadingSystemSettings">
      <div class="panel-head">
        <div>
          <h3>系统设置</h3>
          <p class="panel-tip">除密钥外，任务默认值和 LLM 运行参数都从数据库读取，可在这里直接修改。</p>
        </div>
        <el-tag :type="llmModeTagType" effect="light">当前模式：{{ systemForm.effective_llm_mode }}</el-tag>
      </div>

      <el-alert
        :title="
          systemForm.has_openai_api_key
            ? '已检测到环境变量中的 API Key；页面只管理非敏感参数。'
            : '当前未检测到环境变量中的 API Key；auto 模式会自动回退到 Mock。'
        "
        :type="systemForm.has_openai_api_key ? 'info' : 'warning'"
        show-icon
        :closable="false"
        class="settings-alert"
      />

      <el-form label-position="top">
        <div class="settings-grid">
          <el-form-item label="默认目标 AIGC 率(%)">
            <el-input-number v-model="systemForm.default_target_score" :min="1" :max="100" />
          </el-form-item>
          <el-form-item label="默认最大轮次">
            <el-input-number v-model="systemForm.default_max_rounds" :min="1" :max="10" />
          </el-form-item>
          <el-form-item label="默认策略">
            <el-select v-model="systemForm.default_style">
              <el-option
                v-for="item in runtimeStyleOptions"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="LLM 模式">
            <el-select v-model="systemForm.use_mock_llm">
              <el-option label="auto" value="auto" />
              <el-option label="强制 mock" value="true" />
              <el-option label="强制 real" value="false" />
            </el-select>
          </el-form-item>
          <el-form-item label="OpenAI Base URL">
            <el-input v-model="systemForm.openai_base_url" />
          </el-form-item>
          <el-form-item label="OpenAI Model">
            <el-input v-model="systemForm.openai_model" />
          </el-form-item>
          <el-form-item label="超时(秒)">
            <el-input-number v-model="systemForm.openai_timeout_seconds" :min="1" :max="3600" />
          </el-form-item>
          <el-form-item label="重试次数">
            <el-input-number v-model="systemForm.openai_max_retries" :min="0" :max="20" />
          </el-form-item>
        </div>

        <div class="prompt-actions">
          <el-button
            type="primary"
            :loading="savingSystemSettings || loadingSystemSettings"
            @click="saveSystemSettings"
          >
            保存系统设置
          </el-button>
          <el-button :loading="loadingSystemSettings" @click="loadSystemSettings">重新加载</el-button>
        </div>
      </el-form>
    </article>

    <div class="grid-two">
      <article class="app-card panel">
        <h3>用户管理</h3>
        <p class="panel-tip">创建账号并分配角色，权限即时生效。</p>
        <div class="create-form">
          <el-input v-model="createForm.username" placeholder="用户名" />
          <el-input v-model="createForm.password" placeholder="密码" type="password" show-password />
          <el-select v-model="createForm.role">
            <el-option label="admin" value="admin" />
            <el-option label="operator" value="operator" />
            <el-option label="viewer" value="viewer" />
          </el-select>
          <el-button type="primary" @click="createNewUser">创建</el-button>
        </div>

        <el-table :data="users" v-loading="loadingUsers">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="username" label="用户名" min-width="130" />
          <el-table-column label="角色" min-width="160">
            <template #default="{ row }">
              <el-select
                :model-value="row.roles[0]"
                size="small"
                @change="(value: string) => changeRole(row.id, value)"
              >
                <el-option label="admin" value="admin" />
                <el-option label="operator" value="operator" />
                <el-option label="viewer" value="viewer" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="170">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString() }}
            </template>
          </el-table-column>
        </el-table>
      </article>

      <article class="app-card panel">
        <h3>Prompt 管理</h3>
        <p class="panel-tip">支持在线查看、编辑和保存 Prompt 文件内容。</p>
        <el-table
          :data="prompts"
          v-loading="loadingPrompts"
          class="prompt-table"
          :row-class-name="promptRowClassName"
          @row-click="selectPrompt"
        >
          <el-table-column prop="group" label="Group" width="90" />
          <el-table-column prop="name" label="Name" width="130" />
          <el-table-column prop="version" label="Version" width="110" />
          <el-table-column label="Variables" min-width="180">
            <template #default="{ row }">
              {{ row.variables.join(", ") }}
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="!promptLabel" description="暂无 Prompt 数据" />
        <el-form v-else label-position="top" class="prompt-form" v-loading="loadingPromptDetail">
          <div class="prompt-head">
            <el-form-item label="Prompt">
              <el-input :model-value="promptLabel" readonly />
            </el-form-item>
            <el-form-item label="版本">
              <el-input v-model="promptForm.version" />
            </el-form-item>
          </div>

          <el-form-item label="Variables（逗号或换行分隔）">
            <el-input v-model="promptForm.variablesText" type="textarea" :rows="2" />
          </el-form-item>

          <template v-if="promptForm.group === 'rewrite'">
            <el-form-item label="System">
              <el-input v-model="promptForm.system" type="textarea" :rows="7" />
            </el-form-item>
            <el-form-item label="Human">
              <el-input v-model="promptForm.human" type="textarea" :rows="10" />
            </el-form-item>
          </template>

          <template v-else>
            <el-form-item label="Instruction">
              <el-input v-model="promptForm.instruction" type="textarea" :rows="12" />
            </el-form-item>
          </template>

          <div class="prompt-actions">
            <el-button
              type="primary"
              :loading="savingPrompt || loadingPromptDetail"
              @click="savePromptChanges"
            >
              保存 Prompt
            </el-button>
            <el-button :disabled="!promptLabel" :loading="loadingPromptDetail" @click="reloadCurrentPrompt">
              重新加载当前
            </el-button>
          </div>
        </el-form>
      </article>
    </div>
  </section>
</template>

<style scoped>
.alert {
  margin-bottom: 14px;
}

.page-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.panel {
  padding: 16px;
}

.panel h3 {
  margin: 0;
}

.panel-tip {
  margin: 6px 0 12px;
  font-size: 12px;
  color: #69809b;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.settings-panel {
  margin-bottom: 14px;
}

.settings-alert {
  margin: 12px 0;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px 12px;
}

.create-form {
  display: grid;
  grid-template-columns: 1.1fr 1.1fr 120px 90px;
  gap: 8px;
  margin-bottom: 12px;
}

.prompt-table {
  margin-bottom: 14px;
}

.prompt-form {
  margin-top: 8px;
  border-top: 1px dashed #d7e3f1;
  padding-top: 12px;
}

.prompt-head {
  display: grid;
  grid-template-columns: 1fr 180px;
  gap: 10px;
}

.prompt-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

:deep(.is-selected-row > td) {
  background: rgba(64, 158, 255, 0.12) !important;
}

@media (max-width: 1200px) {
  .prompt-head,
  .settings-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .page-actions {
    justify-content: flex-start;
  }

  .panel-head {
    flex-direction: column;
  }

  .create-form,
  .settings-grid,
  .prompt-head {
    grid-template-columns: 1fr;
  }
}
</style>
