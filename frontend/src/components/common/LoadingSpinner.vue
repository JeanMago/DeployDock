<script setup lang="ts">
import { Loader2 } from 'lucide-vue-next';
withDefaults(defineProps<{ size?: string; class?: string }>(), { size: 'w-6 h-6', class: 'text-dock-accent' });
</script>
<template>
  <Loader2 :class="['animate-spin', size, $props.class]" />
</template>
