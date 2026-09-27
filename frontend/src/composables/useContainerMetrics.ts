import { ref } from 'vue';
import { useWebSocket } from './useWebSocket';
import type { ContainerStats } from '@/services/types';

export function useContainerMetrics(containerId: string) {
  const metrics = ref<ContainerStats[]>([]);
  const MAX_POINTS = 30;

  const { status, disconnect } = useWebSocket(`/ws/containers/${containerId}/stats`, (data: ContainerStats) => {
    metrics.value.push(data);
    if (metrics.value.length > MAX_POINTS) {
      metrics.value.shift();
    }
  });

  return { metrics, status, disconnect };
}
