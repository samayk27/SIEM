import { z } from 'zod'

export const labEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  event_type: z.string().nullable(),
  username: z.string().nullable(),
  source_ip: z.string().nullable(),
  severity: z.string(),
  metadata: z.record(z.string(), z.unknown()),
})

export const labOverviewSchema = z.object({
  tenant: z.object({
    name: z.string(),
    environment: z.string(),
    status: z.string(),
  }),
  users: z.array(z.record(z.string(), z.unknown())),
  resources: z.array(z.record(z.string(), z.unknown())),
  policies: z.record(z.string(), z.union([z.string(), z.number(), z.boolean()])),
  blocked_ips: z.array(z.string()),
  revoked_sessions: z.array(z.string()),
  recent_events: z.array(labEventSchema),
})

export type LabOverview = z.infer<typeof labOverviewSchema>
export type LabAction =
  | 'login_failure'
  | 'login_success'
  | 'file_download'
  | 'privilege_change'
  | 'api_request'
  | 'device_register'
  | 'restricted_access'
  | 'disable_user'
  | 'block_ip'
  | 'revoke_session'

export interface LabActionRequest {
  action: LabAction
  username?: string
  source_ip?: string
  resource?: string
  target_username?: string
  role?: string
}

export interface LabActionResult {
  action: {
    action: LabAction
    username: string
    source_ip: string
    resource: string
    control: string
    blocked: boolean
    timestamp: string
  }
  message: string
  event: unknown
  control: string
  blocked: boolean
}
