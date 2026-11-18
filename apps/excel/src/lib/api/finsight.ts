import { QueryResult } from '../../types/api';

export const fetchQueryResult = async (query: string): Promise<QueryResult> => {
  // Simulate API call
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ id: '1', data: `Result for ${query}` });
    }, 1000);
  });
};
