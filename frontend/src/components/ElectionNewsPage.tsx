"use client";

import { useCallback, useState } from "react";
import { ArticleList } from "@/components/ArticleList";
import { SearchBar } from "@/components/SearchBar";
import { SelectedFilterChips } from "@/components/SelectedFilterChips";
import { FilterType } from "@/lib/articles";
import { useInfiniteArticles } from "@/hooks/useInfiniteArticles";

type SelectedFilters = {
  parties: string[];
  regions: string[];
  people: string[];
};

const addUnique = (values: string[], nextValue: string) =>
  values.includes(nextValue) ? values : [...values, nextValue];

export function ElectionNewsPage() {
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<SelectedFilters>({
    parties: ["Democratic Party", "People Power Party"],
    regions: ["Seoul", "Busan"],
    people: ["Hong Gil-dong"],
  });

  const { articles, isLoading, hasMore, error, loadMore } = useInfiniteArticles({
    query,
    ...filters,
  });

  const addFilter = useCallback((type: FilterType, value: string) => {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [type]: addUnique(currentFilters[type], value),
    }));
  }, []);

  const removeFilter = useCallback((type: FilterType, value: string) => {
    setFilters((currentFilters) => ({
      ...currentFilters,
      [type]: currentFilters[type].filter((currentValue) => currentValue !== value),
    }));
  }, []);

  return (
    <main className="min-h-screen px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl">
        <header className="mb-6">
          <h1 className="text-3xl font-bold tracking-normal text-white sm:text-5xl">Election News Summary</h1>
        </header>

        <div className="sticky top-0 z-10 -mx-4 border-b border-line bg-ink/90 px-4 py-4 backdrop-blur sm:mx-0 sm:rounded-lg sm:border">
          <SearchBar value={query} onChange={setQuery} />
          <div className="mt-4">
            <SelectedFilterChips
              parties={filters.parties}
              regions={filters.regions}
              people={filters.people}
              onRemoveFilter={removeFilter}
            />
          </div>
        </div>

        <ArticleList
          articles={articles}
          isLoading={isLoading}
          hasMore={hasMore}
          error={error}
          onLoadMore={loadMore}
          onAddFilter={addFilter}
        />
      </div>
    </main>
  );
}
