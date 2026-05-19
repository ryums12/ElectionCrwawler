"use client";

import { FilterType } from "@/lib/articles";

type FilterChip = {
  type: FilterType;
  label: string;
  value: string;
};

type SelectedFilterChipsProps = {
  parties: string[];
  regions: string[];
  people: string[];
  onRemoveFilter: (type: FilterType, value: string) => void;
};

const getChips = ({ parties, regions, people }: Omit<SelectedFilterChipsProps, "onRemoveFilter">): FilterChip[] => [
  ...parties.map((value) => ({ type: "parties" as const, label: "Party", value })),
  ...regions.map((value) => ({ type: "regions" as const, label: "Region", value })),
  ...people.map((value) => ({ type: "people" as const, label: "Person", value })),
];

export function SelectedFilterChips({ parties, regions, people, onRemoveFilter }: SelectedFilterChipsProps) {
  const chips = getChips({ parties, regions, people });

  if (chips.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2" aria-label="Selected filters">
      {chips.map((chip) => (
        <span
          key={`${chip.type}-${chip.value}`}
          className="inline-flex max-w-full items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900 shadow-sm dark:border-violet-300/20 dark:bg-violet-500/15 dark:text-violet-100"
        >
          <span className="truncate">
            {chip.value}
          </span>
          <button
            type="button"
            onClick={() => onRemoveFilter(chip.type, chip.value)}
            className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-white text-xs font-semibold text-slate-500 transition hover:bg-blue-600 hover:text-white focus:outline-none focus:ring-2 focus:ring-blue-300 dark:bg-slate-900/80 dark:text-slate-300 dark:hover:bg-violet-300 dark:hover:text-slate-950 dark:focus:ring-violet-300"
            aria-label={`Remove ${chip.label}: ${chip.value}`}
          >
            X
          </button>
        </span>
      ))}
    </div>
  );
}
