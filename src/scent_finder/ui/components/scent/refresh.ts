import type { QueryClient } from "@tanstack/react-query";

/** Refetch everything derived from my_collection / wear_log. */
export function refreshWardrobe(queryClient: QueryClient) {
  return queryClient.invalidateQueries({
    predicate: (q) => {
      const key = String(q.queryKey[0] ?? "");
      return key.startsWith("/api/collection") || key === "/api/dna" || key === "/api/me";
    },
  });
}
