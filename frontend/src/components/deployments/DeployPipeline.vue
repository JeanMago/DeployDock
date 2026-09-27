<script setup lang="ts">
import { Check, X, Loader2 } from 'lucide-vue-next';
const steps = ['Webhook', 'Clone', 'Build', 'Deploy', 'Health Check'];
defineProps<{ currentStep: number, status: string }>();
</script>

<template>
  <div class="flex items-center justify-between w-full max-w-3xl mx-auto py-6">
    <template v-for="(step, idx) in steps" :key="idx">
      <div class="flex flex-col items-center relative z-10">
        <div 
          class="w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors shadow-lg bg-dock-bg"
          :class="[
            idx < currentStep ? 'border-dock-success text-dock-success shadow-[0_0_12px_rgba(34,197,94,0.3)]' : 
            idx === currentStep ? (status === 'failed' ? 'border-dock-error text-dock-error shadow-[0_0_12px_rgba(239,68,68,0.3)]' : 'border-dock-accent text-dock-accent shadow-[0_0_12px_rgba(14,165,233,0.3)]') : 
            'border-dock-border text-dock-text-dim'
          ]"
        >
          <Check v-if="idx < currentStep" class="w-5 h-5" />
          <X v-else-if="idx === currentStep && status === 'failed'" class="w-5 h-5" />
          <Loader2 v-else-if="idx === currentStep" class="w-5 h-5 animate-spin" />
          <span v-else class="text-sm font-medium">{{ idx + 1 }}</span>
        </div>
        <span class="mt-2 text-xs font-medium" :class="idx <= currentStep ? 'text-dock-text' : 'text-dock-text-dim'">{{ step }}</span>
      </div>
      <div v-if="idx < steps.length - 1" class="flex-1 h-0.5 mx-2 bg-dock-border relative">
        <div class="absolute inset-0 bg-dock-success transition-all duration-500" :style="{ width: idx < currentStep ? '100%' : '0%' }"></div>
      </div>
    </template>
  </div>
</template>
