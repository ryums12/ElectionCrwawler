"use client";

import { useEffect, useRef } from "react";
import { Article, FilterType } from "@/lib/articles";
import { ArticleCard } from "@/components/ArticleCard";

type ArticleListProps = {
  articles: Article[];
  isLoading: boolean;
  hasMore: boolean;
  error: string | null;
  onLoadMore: () => void;
  onRetry: () => void;
  onAddFilter: (type: FilterType, value: string) => void;
};

export function ArticleList({
  articles,
  isLoading,
  hasMore,
  error,
  onLoadMore,
  onRetry,
  onAddFilter,
}: ArticleListProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;

    if (!sentinel) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !isLoading && !error) {
          onLoadMore();
        }
      },
      { rootMargin: "360px" },
    );

    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [error, hasMore, isLoading, onLoadMore]);

  return (
    <section className="mt-8" aria-label="Article summaries">
      <div className="space-y-4">
        {articles.map((article) => (
          <ArticleCard key={article.id} article={article} onAddFilter={onAddFilter} />
        ))}
      </div>

      {!isLoading && articles.length === 0 && !error ? (
        <div className="rounded-lg border border-slate-200 bg-white/80 p-8 text-center text-slate-600 dark:border-line dark:bg-panel/70 dark:text-slate-300">
          No articles match the current search.
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-400/30 dark:bg-red-950/40 dark:text-red-100">
          <p>{error}</p>
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 transition hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-200 dark:border-red-300/40 dark:text-red-50 dark:hover:bg-red-400/10"
          >
            Retry
          </button>
        </div>
      ) : null}

      <div ref={sentinelRef} className="h-12" aria-hidden="true" />

      {isLoading ? (
        <p className="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Loading articles...</p>
      ) : null}

      {!hasMore && articles.length > 0 ? (
        <p className="py-4 text-center text-sm text-slate-500 dark:text-slate-400">No more articles to load.</p>
      ) : null}
    </section>
  );
}
