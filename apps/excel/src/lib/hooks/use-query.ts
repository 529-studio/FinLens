import { useQuery } from '@tanstack/react-query';
import { fetchQueryResult } from '../api/finsight';

export const useFinsightQuery = (query: string, documentId?: string) => {
  return useQuery({
    queryKey: ['finsight-query', query, documentId],
    queryFn: () => fetchQueryResult(query, documentId),
    enabled: !!query,
  });
};
