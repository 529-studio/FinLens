/* global CustomFunctions, Excel */

/**
 * @customfunction
 * @param query The query to execute
 * @returns The result of the query
 */
export async function FINTRACE_QUERY(query: string): Promise<string> {
  if (typeof Excel !== 'undefined' && typeof Excel.run === 'function') {
    return Excel.run(async (_context) => {
      return `Query executed: ${query}`;
    });
  }
  return `Query executed: ${query}`;
}

/**
 * Backward compatibility alias for FINTRACE_QUERY
 * @customfunction
 */
export const FINSIGHT_QUERY = FINTRACE_QUERY;

const globalObj = globalThis as Record<string, any>;
if (globalObj.CustomFunctions && typeof globalObj.CustomFunctions.associate === 'function') {
  globalObj.CustomFunctions.associate('FINTRACE_QUERY', FINTRACE_QUERY);
  globalObj.CustomFunctions.associate('FINSIGHT_QUERY', FINSIGHT_QUERY);
} else {
  globalObj.__FINTRACE_CUSTOM_FUNCTIONS__ = {
    FINTRACE_QUERY,
    FINSIGHT_QUERY,
  };
}
