import { ref, type Ref } from 'vue';

export function useApi<T, Args extends any[]>(
  apiFunc: (...args: Args) => Promise<T>,
  initialValue: T | null = null
) {
  const data = ref<T | null>(initialValue) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<string | null>(null);

  const execute = async (...args: Args): Promise<T | null> => {
    loading.value = true;
    error.value = null;
    try {
      const result = await apiFunc(...args);
      data.value = result;
      return result;
    } catch (err: any) {
      error.value = err.message || 'An error occurred';
      return null;
    } finally {
      loading.value = false;
    }
  };

  return { data, loading, error, execute };
}
