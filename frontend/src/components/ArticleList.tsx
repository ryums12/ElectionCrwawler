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
  onAddFilter: (type: FilterType, value: string) => void;
};

export function ArticleList({ articles, isLoading, hasMore, error, onLoadMore, onAddFilter }: ArticleListProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;

    if (!sentinel) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !isLoading) {
          onLoadMore();
        }
      },
      { rootMargin: "360px" },
    );

    observer.observe(sentinel);

    return () => observer.disconnect();
  }, [hasMore, isLoading, onLoadMore]);

  return (
    <section className="mt-8" aria-label="Article summaries">
      <div className="space-y-4">
        {articles.map((article) => (
          <ArticleCard key={article.id} article={article} onAddFilter={onAddFilter} />
        ))}
      </div>

      {!isLoading && articles.length === 0 && !error ? (
        <div className="rounded-lg border border-line bg-panel/70 p-8 text-center text-slate-300">
          No articles match the current search.
        </div>
      ) : null}

      {error ? (
        <div className="mt-4 rounded-lg border border-red-400/30 bg-red-950/40 p-4 text-sm text-red-100">{error}</div>
      ) : null}

      <div ref={sentinelRef} className="h-12" aria-hidden="true" />

      {isLoading ? <p className="py-4 text-center text-sm text-slate-400">Loading articles...</p> : null}

      {!hasMore && articles.length > 0 ? (
        <p className="py-4 text-center text-sm text-slate-500">No more articles to load.</p>
      ) : null}
    </section>
  );
}
