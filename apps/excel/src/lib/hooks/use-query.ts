import { useQuery } from '@tanstack/react-query';
import { fetchQueryResult } from '../api/finsight';

export const useFinsightQuery = (query: string) => {
  return useQuery({
    queryKey: ['finsight-query', query],
    queryFn: () => fetchQueryResult(query),
    enabled: !!query,
  });
};
