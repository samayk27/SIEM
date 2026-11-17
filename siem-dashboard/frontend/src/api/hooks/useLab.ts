import {
  type UseMutationResult,
  type UseQueryResult,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { toast } from 'sonner'
import type { LabActionRequest, LabActionResult, LabOverview } from '@/api/types'
import { API_ENDPOINTS, QUERY_KEYS } from '@/config'
import { apiClient } from '@/core/lib'

export const useLabOverview = (): UseQueryResult<LabOverview, Error> => {
  return useQuery({
    queryKey: QUERY_KEYS.LAB.OVERVIEW(),
    queryFn: async () => {
      const response = await apiClient.get<LabOverview>(
        API_ENDPOINTS.LAB.OVERVIEW
      )
      return response.data
    },
    refetchInterval: 3000,
  })
}

export const useLabAction = (): UseMutationResult<
  LabActionResult,
  Error,
  LabActionRequest
> => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: LabActionRequest) => {
      const response = await apiClient.post<LabActionResult>(
        API_ENDPOINTS.LAB.ACTIONS,
        payload
      )
      return response.data
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LAB.ALL })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.LOGS.ALL })
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.ALERTS.ALL })
      toast[result.blocked ? 'warning' : 'success'](
        result.blocked ? result.message : 'Enterprise action completed'
      )
    },
    onError: (error) => toast.error(error.message),
  })
}
