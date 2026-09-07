// 与后端 app/schemas/auth.py 对齐的类型（Backend API contract is the source of truth）。

export interface UsernamePasswordPayload {
  username: string
  password: string
}

export interface UserOut {
  user_id: string
  username: string
  created_at: string | null
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
