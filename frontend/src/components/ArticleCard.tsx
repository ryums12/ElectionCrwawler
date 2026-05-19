"use client";

import { Article, FilterType } from "@/lib/articles";
import { getPartyColor, getReadableTextColor } from "@/lib/partyColors";

type ArticleCardProps = {
  article: Article;
  onAddFilter: (type: FilterType, value: string) => void;
};

const filterGroups: { type: FilterType; label: string; isParty?: boolean }[] = [
  { type: "parties", label: "party", isParty: true },
  { type: "regions", label: "region" },
  { type: "people", label: "person" },
];

export function ArticleCard({ article, onAddFilter }: ArticleCardProps) {
  const href = article.originalUrl || article.naverUrl || "#";
  const body = article.summary || article.description;

  return (
    <article className="rounded-lg border border-slate-200 bg-white/90 p-5 shadow-sm backdrop-blur transition dark:border-line dark:bg-panel/80 dark:shadow-glow">
      <h2 className="text-lg font-semibold leading-snug text-slate-950 sm:text-xl dark:text-slate-50">
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="outline-none transition hover:text-blue-700 focus:text-blue-700 dark:hover:text-violet-300 dark:focus:text-violet-300"
        >
          {article.title}
        </a>
      </h2>

      {body ? (
        <p className="line-clamp-3 mt-3 text-sm leading-6 text-slate-700 sm:text-base dark:text-slate-300">{body}</p>
      ) : null}

      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
        {article.sourceName ? <span>{article.sourceName}</span> : null}
        {article.publishedAt ? <time dateTime={article.publishedAt}>{formatDate(article.publishedAt)}</time> : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {filterGroups.flatMap(({ type, label, isParty }) =>
          article[type].map((value) => {
            const partyColor = isParty ? getPartyColor(value) : undefined;
            const textColor = partyColor ? getReadableTextColor(partyColor) : undefined;

            return (
              <button
                type="button"
                key={`${type}-${value}`}
                onClick={() => onAddFilter(type, value)}
                className={
                  isParty
                    ? "rounded-full border border-transparent px-3 py-1.5 text-xs font-semibold shadow-sm transition hover:brightness-110 focus:outline-none focus:ring-2 focus:ring-blue-300 dark:focus:ring-violet-300"
                    : "rounded-full border border-slate-300 bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:border-blue-400 hover:bg-blue-50 hover:text-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-300 dark:border-slate-600/80 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-violet-300 dark:hover:bg-violet-500/20 dark:hover:text-violet-100 dark:focus:ring-violet-300"
                }
                style={partyColor && textColor ? { backgroundColor: partyColor, color: textColor } : undefined}
                aria-label={`Add ${label} filter: ${value}`}
              >
                {value}
              </button>
            );
          }),
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
