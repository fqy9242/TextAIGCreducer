<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useAuthStore } from "@/stores/auth";
import logoUrl from "@/assets/logo.png";

const router = useRouter();
const authStore = useAuthStore();

const form = reactive({
  username: "admin",
  password: "Admin@123456",
});
const loading = ref(false);

async function onSubmit() {
  loading.value = true;
  try {
    await authStore.login(form.username, form.password);
    await router.push({ name: "workspace" });
  } catch (error: any) {
    const message = error?.response?.data?.detail ?? "登录失败，请检查账号或服务状态";
    ElMessage.error(String(message));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧介绍区 -->
      <section class="intro-section">
        <div class="intro-content">
          <div class="brand-header">
            <img :src="logoUrl" alt="TextOps Logo" class="brand-logo" />
            <div class="brand-badge">TextOps Console</div>
          </div>
          
          <h1 class="brand-title">文本改写与AIGC 风险控制系统</h1>
          <p class="brand-desc">
            "用魔法打败魔法 通过AI降低AI率"
          </p>

          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              </div>
              <div class="metric-info">
                <div class="metric-value">自定义</div>
                <div class="metric-label">查重阈值</div>
              </div>
            </div>
            <div class="metric-item">
              <div class="metric-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg>
              </div>
              <div class="metric-info">
                <div class="metric-value">多轮</div>
                <div class="metric-label">迭代轮次</div>
              </div>
            </div>
            <div class="metric-item">
              <div class="metric-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
              </div>
              <div class="metric-info">
                <div class="metric-value">自定义</div>
                <div class="metric-label">策略模式</div>
              </div>
            </div>
          </div>

          <!-- <ul class="feature-list">
            <li>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              改写 → 检测 → 决策闭环自动执行
            </li>
            <li>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              任务状态与迭代轨迹全程可追踪
            </li>
            <li>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              管理员在线管理 Prompt 与用户权限
            </li>
          </ul> -->
        </div>
      </section>

      <!-- 右侧登录表单 -->
      <section class="form-section">
        <div class="login-card app-card">
          <div class="form-header">
            <h2 class="form-title">控制台登录</h2>
            <p class="form-subtitle">请输入管理员或业务账号</p>
          </div>

          <el-form label-position="top" @submit.prevent class="login-form">
            <el-form-item label="用户名">
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                prefix-icon="User"
                size="large"
              />
            </el-form-item>
            <el-form-item label="密码">
              <el-input
                v-model="form.password"
                type="password"
                show-password
                placeholder="请输入密码"
                prefix-icon="Lock"
                size="large"
              />
            </el-form-item>

            <el-button
              type="primary"
              :loading="loading"
              class="submit-btn"
              size="large"
              @click="onSubmit"
            >
              进入工作台
            </el-button>
          </el-form>

          <div class="form-footer">
            学习测试使用,请勿用于非法用途!
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background-color: var(--bg-page);
}

.login-container {
  width: 100%;
  max-width: 1100px;
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 48px;
  align-items: center;
}

/* ===== 左侧介绍区 ===== */
.intro-section {
  padding-right: 24px;
}

.brand-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.brand-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  box-shadow: var(--shadow-soft);
}

.brand-badge {
  display: inline-flex;
  align-items: center;
  height: 26px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--brand-600);
  background-color: var(--el-color-primary-light-9);
  border-radius: 999px;
}

.brand-title {
  margin: 0 0 16px;
  font-size: 36px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.brand-desc {
  margin: 0 0 32px;
  font-size: 15px;
  line-height: 1.6;
  color: var(--text-secondary);
  max-width: 480px;
}

.metrics-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background-color: var(--bg-surface);
  border: 1px solid var(--line-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-soft);
}

.metric-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background-color: var(--el-color-primary-light-9);
  color: var(--brand-600);
}

.metric-info {
  display: flex;
  flex-direction: column;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.metric-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-primary);
}

.feature-list li svg {
  color: #52c41a;
  flex-shrink: 0;
}

/* ===== 右侧登录表单 ===== */
.login-card {
  padding: 40px;
  background: var(--bg-surface);
  border-radius: 16px;
}

.form-header {
  margin-bottom: 32px;
}

.form-title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
}

.form-subtitle {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.login-form :deep(.el-form-item__label) {
  padding-bottom: 4px;
}

.submit-btn {
  width: 100%;
  margin-top: 12px;
  height: 44px;
  font-size: 15px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 12px;
  color: var(--text-secondary);
}

/* ===== 响应式 ===== */
@media (max-width: 992px) {
  .login-container {
    grid-template-columns: 1fr;
    max-width: 500px;
    gap: 40px;
  }
  
  .intro-section {
    padding-right: 0;
  }
  
  .brand-title {
    font-size: 28px;
  }
}
</style>
