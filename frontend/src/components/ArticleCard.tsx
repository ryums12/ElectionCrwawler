"use client";

import { Article, FilterType } from "@/lib/articles";

type ArticleCardProps = {
  article: Article;
  onAddFilter: (type: FilterType, value: string) => void;
};

const filterGroups: { type: FilterType; label: string }[] = [
  { type: "parties", label: "Party" },
  { type: "regions", label: "Region" },
  { type: "people", label: "Person" },
];

export function ArticleCard({ article, onAddFilter }: ArticleCardProps) {
  const href = article.originalUrl || article.naverUrl || "#";
  const body = article.summary || article.description;

  return (
    <article className="rounded-lg border border-line bg-panel/80 p-5 shadow-glow backdrop-blur">
      <h2 className="text-lg font-semibold leading-snug text-slate-50 sm:text-xl">
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="outline-none transition hover:text-violet-300 focus:text-violet-300"
        >
          {article.title}
        </a>
      </h2>

      {body ? <p className="line-clamp-3 mt-3 text-sm leading-6 text-slate-300 sm:text-base">{body}</p> : null}

      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
        {article.sourceName ? <span>{article.sourceName}</span> : null}
        {article.publishedAt ? <time dateTime={article.publishedAt}>{formatDate(article.publishedAt)}</time> : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {filterGroups.flatMap(({ type, label }) =>
          article[type].map((value) => (
            <button
              type="button"
              key={`${type}-${value}`}
              onClick={() => onAddFilter(type, value)}
              className="rounded-full border border-slate-600/80 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:border-violet-300 hover:bg-violet-500/20 hover:text-violet-100 focus:outline-none focus:ring-2 focus:ring-violet-300"
              aria-label={`Add ${label} filter: ${value}`}
            >
              {label}: {value}
            </button>
          )),
        )}
      </div>
    </article>
  );
}

const formatDate = (value: string) =>
  new Intl.DateTimeFormat("ko-KR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
