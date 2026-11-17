// ===================
// ©AngelaMos | 2026
// useAlerts.ts
//
// React Query hooks for the alerts API: list, detail, and status update
//
// useAlerts fetches a paginated, filterable list of alerts polled every 10
// seconds. useAlertDetail fetches a single alert with its matched log events.
// useUpdateAlertStatus patches the alert status and invalidates the full
// alerts cache on success.
//
// Key exports:
//   useAlerts - paginated alert list with status/severity filtering
//   useAlertDetail - single alert with matched events
//   useUpdateAlertStatus - mutation to transition alert lifecycle state
//
// Connects to:
//   api.ts, config.ts - HTTP client and endpoint/key constants
//   alert.types.ts - Alert, AlertDetail, AlertStatusUpdateRequest types
// ===================

import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import type {
  Alert,
  AlertDetail,
  AlertQueryParams,
  AlertStatusUpdateRequest,
  PaginatedResponse,
} from '@/api/types'
import { API_ENDPOINTS, QUERY_KEYS } from '@/config'
import { apiClient, QUERY_STRATEGIES } from '@/core/lib'

export const alertQueries = {
  all: () => QUERY_KEYS.ALERTS.ALL,
  list: (params: AlertQueryParams) => QUERY_KEYS.ALERTS.LIST(params),
  byId: (id: string) => QUERY_KEYS.ALERTS.BY_ID(id),
} as const

export const useAlerts = (
  params: AlertQueryParams = {}
): UseQueryResult<PaginatedResponse<Alert>, Error> => {
  return useQuery({
    queryKey: alertQueries.list(params),
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<Alert>>(
        API_ENDPOINTS.ALERTS.LIST,
        { params }
      )
      return response.data
    },
    ...QUERY_STRATEGIES.frequent,
  })
}

export const useAlertDetail = (
  alertId: string
): UseQueryResult<AlertDetail, Error> => {
  return useQuery({
    queryKey: alertQueries.byId(alertId),
    queryFn: async () => {
      const response = await apiClient.get<AlertDetail>(
        API_ENDPOINTS.ALERTS.BY_ID(alertId)
      )
      return response.data
    },
    enabled: alertId.length > 0,
  })
}

export const useUpdateAlertStatus = (
  alertId: string
): UseMutationResult<Alert, Error, AlertStatusUpdateRequest> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: AlertStatusUpdateRequest) => {
      const response = await apiClient.patch<Alert>(
        API_ENDPOINTS.ALERTS.STATUS(alertId),
        payload
      )
      return response.data
    },
    onSuccess: (): void => {
      queryClient.invalidateQueries({ queryKey: alertQueries.all() })
      toast.success('Alert status updated')
    },
    onError: (error: Error): void => {
      toast.error(error.message)
    },
  })
}
