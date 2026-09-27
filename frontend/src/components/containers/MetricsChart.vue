<script setup lang="ts">
import { computed } from 'vue';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Filler);

const props = defineProps<{
  data: number[];
  labels: string[];
  label: string;
  color: string;
  max?: number;
}>();

const chartData = computed(() => ({
  labels: props.labels.length ? props.labels : Array(props.data.length || 10).fill(''),
  datasets: [
    {
      label: props.label,
      data: props.data,
      borderColor: props.color,
      backgroundColor: (context: any) => {
        const ctx = context.chart.ctx;
        const gradient = ctx.createLinearGradient(0, 0, 0, context.chart.height);
        gradient.addColorStop(0, `${props.color}40`);
        gradient.addColorStop(1, `${props.color}00`);
        return gradient;
      },
      borderWidth: 2,
      pointRadius: 0,
      pointHoverRadius: 4,
      fill: true,
      tension: 0.4
    }
  ]
}));

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  plugins: {
    legend: { display: false },
    tooltip: { mode: 'index' as const, intersect: false, backgroundColor: '#0f1629', titleColor: '#94a3b8', bodyColor: '#e2e8f0', borderColor: '#1e2a45', borderWidth: 1 }
  },
  scales: {
    x: { display: false },
    y: {
      display: true,
      min: 0,
      max: props.max,
      grid: { color: '#1e2a45', drawBorder: false },
      ticks: { color: '#64748b', maxTicksLimit: 5, callback: (v: any) => v + (props.label.includes('%') ? '%' : '') }
    }
  },
  interaction: { mode: 'nearest' as const, axis: 'x' as const, intersect: false }
};
</script>

<template>
  <div class="glass-panel p-4 h-64 flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-sm font-medium text-dock-text-muted">{{ label }}</h3>
      <span class="text-xl font-bold font-mono" :style="{ color: color }">
        {{ (data[data.length - 1] || 0).toFixed(2) }}{{ label.includes('%') ? '%' : '' }}
      </span>
    </div>
    <div class="flex-1 relative w-full h-full">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>
