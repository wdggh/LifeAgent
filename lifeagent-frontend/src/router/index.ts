import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('../views/Register.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('../components/AppShell.vue'),
      children: [
        { path: '', redirect: { name: 'chat' } },
        { path: 'chat', name: 'chat', component: () => import('../views/Chat.vue') },
        {
          path: 'chat/:conversationId',
          name: 'conversation',
          component: () => import('../views/Chat.vue'),
        },
        {
          path: 'documents',
          name: 'documents',
          component: () => import('../views/Documents.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'chat' } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const isPublic = to.meta.public === true

  if (!auth.token) {
    if (isPublic) return true
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  // 已登录用户不应停留在登录/注册页
  if (isPublic) return { name: 'chat' }

  // 有 token 先经 /auth/me 校验并加载用户；失败(401)由响应拦截器清会话回登录
  const restored = await auth.restore()
  if (!restored && !auth.token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router
