"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Article, ArticleSearchParams, fetchArticles } from "@/lib/articles";

export const PAGE_SIZE = 10;

type UseInfiniteArticlesParams = Pick<ArticleSearchParams, "query" | "parties" | "regions" | "people">;

export const useInfiniteArticles = ({ query, parties, regions, people }: UseInfiniteArticlesParams) => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);
  const isLoadingRef = useRef(false);
  const hasMoreRef = useRef(true);

  const params = useMemo(
    () => ({
      query,
      parties,
      regions,
      people,
    }),
    [people, parties, query, regions],
  );

  const loadPage = useCallback(
    async (nextPage: number, shouldReset = false) => {
      if ((isLoadingRef.current && !shouldReset) || (!hasMoreRef.current && !shouldReset)) {
        return;
      }

      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;
      isLoadingRef.current = true;
      setIsLoading(true);
      setError(null);

      try {
        const result = await fetchArticles({
          ...params,
          page: nextPage,
          limit: PAGE_SIZE,
        });

        if (requestId !== requestIdRef.current) {
          return;
        }

        setArticles((currentArticles) => (shouldReset ? result.articles : [...currentArticles, ...result.articles]));
        setPage(nextPage);
        setHasMore(result.hasMore);
        hasMoreRef.current = result.hasMore;
      } catch (unknownError) {
        if (requestId === requestIdRef.current) {
          setError(unknownError instanceof Error ? unknownError.message : "Could not load articles.");
        }
      } finally {
        if (requestId === requestIdRef.current) {
          isLoadingRef.current = false;
          setIsLoading(false);
        }
      }
    },
    [params],
  );

  useEffect(() => {
    setArticles([]);
    setPage(1);
    setHasMore(true);
    hasMoreRef.current = true;
    void loadPage(1, true);
  }, [loadPage]);

  const loadMore = useCallback(() => {
    void loadPage(page + 1);
  }, [loadPage, page]);

  return {
    articles,
    isLoading,
    hasMore,
    error,
    loadMore,
  };
};
