import { defineStore } from 'pinia'
import * as authApi from '../api/auth'
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from '../api/client'
import type { UserOut, UsernamePasswordPayload } from '../types/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getAccessToken() as string | null,
    user: null as UserOut | null,
  }),

  actions: {
    /** 只注册不登录；注册响应没有 token，自动登录由调用方紧接着触发。 */
    async registerAccount(payload: UsernamePasswordPayload): Promise<void> {
      await authApi.register(payload)
    },

    async login(payload: UsernamePasswordPayload): Promise<void> {
      const { access_token } = await authApi.login(payload)
      setAccessToken(access_token)
      this.token = access_token
      this.user = null
      await this.fetchMe()
    },

    async fetchMe(): Promise<UserOut> {
      const user = await authApi.fetchMe()
      this.user = user
      return user
    },

    /** 启动/路由守卫恢复登录态：有 token 且尚未加载用户时调用 /auth/me。 */
    async restore(): Promise<boolean> {
      if (!this.token) return false
      if (this.user) return true
      try {
        await this.fetchMe()
        return true
      } catch {
        this.user = null
        return false
      }
    },

    /** 后端没有 logout 接口，登出 = 前端清除 token。 */
    logout(): void {
      clearAccessToken()
      this.token = null
      this.user = null
    },
  },
})
