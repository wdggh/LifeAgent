<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { apiErrorMessage } from '../api/errors'
import { useAuthStore } from '../stores/auth'

interface RegisterFormState {
  username: string
  password: string
  confirmPassword: string
}

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive<RegisterFormState>({
  username: '',
  password: '',
  confirmPassword: '',
})

const rules: FormRules<RegisterFormState> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度应为 3–32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 128, message: '密码长度应为 8–128 个字符', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (new Blob([value]).size > 72) {
          callback(new Error('密码过长（UTF-8 不超过 72 字节）'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== form.password) {
          callback(new Error('两次输入的密码不一致'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function handleSubmit(): Promise<void> {
  if (loading.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
  loading.value = true
  try {
    // 第一步：注册（响应没有 token）
    await auth.registerAccount({ username: form.username.trim(), password: form.password })
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '注册失败，请稍后重试'))
    loading.value = false
    return
  }

  // 第二步：自动登录。登录失败不代表注册失败，引导用户直接登录，避免死胡同。
  try {
    await auth.login({ username: form.username.trim(), password: form.password })
    void router.replace(redirect ?? { name: 'chat' })
  } catch {
    ElMessage.warning('注册成功，但自动登录失败，请用刚注册的账号登录')
    void router.replace({ name: 'login', query: { redirect: redirect ?? undefined } })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card">
      <h1 class="auth-title">注册 LifeAgent</h1>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" autocomplete="username" placeholder="3–32 个字符" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="new-password"
            show-password
            placeholder="至少 8 个字符"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            autocomplete="new-password"
            show-password
            placeholder="再次输入密码"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button type="primary" class="auth-submit" :loading="loading" @click="handleSubmit">
          注册并登录
        </el-button>
      </el-form>
      <div class="auth-switch">
        已有账号？
        <RouterLink to="/login">登录</RouterLink>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f7f8fa;
}

.auth-card {
  width: 360px;
}

.auth-title {
  margin: 0 0 20px;
  font-size: 20px;
  text-align: center;
}

.auth-submit {
  width: 100%;
  margin-top: 4px;
}

.auth-switch {
  margin-top: 14px;
  font-size: 13px;
  color: #909399;
  text-align: center;
}
</style>
