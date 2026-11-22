/**
 * @customfunction
 * @param query The query to execute
 * @returns The result of the query
 */
export async function FINTRACE_QUERY(query: string): Promise<string> {
  return Excel.run(async (_context) => {
    // In a real scenario, we would call the desktop interop bridge here
    return `Query executed: ${query}`;
  });
}

/**
 * Backward compatibility alias for FINTRACE_QUERY
 * @customfunction
 */
export const FINSIGHT_QUERY = FINTRACE_QUERY;
