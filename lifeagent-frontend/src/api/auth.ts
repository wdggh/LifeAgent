import apiClient from './client'
import type {
  TokenResponse,
  UserOut,
  UsernamePasswordPayload,
} from '../types/auth'

export async function register(payload: UsernamePasswordPayload): Promise<UserOut> {
  const { data } = await apiClient.post<UserOut>('/auth/register', payload)
  return data
}

export async function login(payload: UsernamePasswordPayload): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', payload)
  return data
}

export async function fetchMe(): Promise<UserOut> {
  const { data } = await apiClient.get<UserOut>('/auth/me')
  return data
}
