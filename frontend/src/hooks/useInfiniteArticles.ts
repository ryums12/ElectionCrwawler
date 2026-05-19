"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Article, ArticleSearchParams, fetchArticles } from "@/lib/articles";

export const PAGE_SIZE = 10;

type UseInfiniteArticlesParams = Pick<ArticleSearchParams, "query" | "parties" | "regions" | "people">;

export const useInfiniteArticles = ({ query, parties, regions, people }: UseInfiniteArticlesParams) => {
  const [articles, setArticles] = useState<Article[]>([]);
  const [nextPage, setNextPage] = useState(1);
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
    async (page: number, shouldReset = false) => {
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
          page,
          limit: PAGE_SIZE,
        });

        if (requestId !== requestIdRef.current) {
          return;
        }

        setArticles((currentArticles) => (shouldReset ? result.items : [...currentArticles, ...result.items]));
        setNextPage(page + 1);
        setHasMore(result.hasMore);
        hasMoreRef.current = result.hasMore;
      } catch (unknownError) {
        if (requestId === requestIdRef.current) {
          setError(unknownError instanceof Error ? unknownError.message : "Could not load articles.");
          setHasMore(false);
          hasMoreRef.current = false;
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
    setNextPage(1);
    setHasMore(true);
    hasMoreRef.current = true;
    void loadPage(1, true);
  }, [loadPage]);

  const loadMore = useCallback(() => {
    void loadPage(nextPage);
  }, [loadPage, nextPage]);

  const retry = useCallback(() => {
    setArticles([]);
    setNextPage(1);
    setHasMore(true);
    hasMoreRef.current = true;
    void loadPage(1, true);
  }, [loadPage]);

  return {
    articles,
    isLoading,
    hasMore,
    error,
    loadMore,
    retry,
  };
};
