import axios, { AxiosError } from 'axios'

import type { TripPlan, TripPlanRequest } from '@/types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 180_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function generateTripPlan(
  request: TripPlanRequest,
): Promise<TripPlan> {
  const response = await api.post<TripPlan>('/trips/plan', request)
  return response.data
}

interface ErrorPayload {
  detail?: string | string[] | Array<{ msg?: string }>
}

export function getApiErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) {
    return '发生未知错误，请稍后重试。'
  }

  if (error.code === 'ECONNABORTED') {
    return '规划时间超过三分钟，请稍后重试或缩短旅行天数。'
  }

  const payload = error.response?.data as ErrorPayload | undefined
  const detail = payload?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) =>
      typeof item === 'string' ? item : item.msg || '',
    )
    const message = messages.filter(Boolean).join('；')
    if (message) return message
  }

  if (!error.response) {
    return '无法连接后端服务，请确认 FastAPI 已在 8000 端口启动。'
  }
  return `请求失败（HTTP ${error.response.status}），请稍后重试。`
}

