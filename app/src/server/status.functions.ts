import { createServerFn } from '@tanstack/react-start'

export const getServerStatus = createServerFn({ method: 'GET' }).handler(() => ({
  status: 'ok' as const,
  serverTime: new Date().toISOString(),
}))
