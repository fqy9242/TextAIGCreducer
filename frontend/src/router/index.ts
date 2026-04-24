import { createRouter, createWebHistory } from "vue-router";
import { tokenStore } from "@/api/client";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
      meta: {
        title: "登录",
      },
    },
    {
      path: "/",
      component: () => import("@/layouts/MainLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: "/workspace",
        },
        {
          path: "workspace",
          name: "workspace",
          component: () => import("@/views/WorkspaceView.vue"),
          meta: {
            title: "工作台",
            subtitle: "提交文本并执行闭环改写检测",
          },
        },
        {
          path: "tasks/:id",
          name: "task-detail",
          component: () => import("@/views/TaskDetailView.vue"),
          meta: {
            title: "任务详情",
            subtitle: "查看结果与迭代轨迹",
          },
        },
        {
          path: "history",
          name: "history",
          component: () => import("@/views/HistoryView.vue"),
          meta: {
            title: "历史任务",
            subtitle: "分页追踪全部改写任务",
          },
        },
        {
          path: "admin",
          name: "admin",
          component: () => import("@/views/AdminView.vue"),
          meta: {
            title: "管理中心",
            subtitle: "用户权限、Prompt 与运行配置管理",
          },
        },
      ],
    },
  ],
});

router.beforeEach((to) => {
  const authed = Boolean(tokenStore.getAccessToken());
  if (to.meta.requiresAuth && !authed) {
    return { name: "login" };
  }
  if (to.name === "login" && authed) {
    return { name: "workspace" };
  }
  return true;
});

export default router;
