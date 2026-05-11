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
          className="inline-flex max-w-full items-center gap-2 rounded-full border border-violet-300/20 bg-violet-500/15 px-3 py-2 text-sm text-violet-100 shadow-sm"
        >
          <span className="truncate">
            {chip.label}: {chip.value}
          </span>
          <button
            type="button"
            onClick={() => onRemoveFilter(chip.type, chip.value)}
            className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-slate-900/80 text-xs font-semibold text-slate-300 transition hover:bg-violet-300 hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-violet-300"
            aria-label={`Remove ${chip.label}: ${chip.value}`}
          >
            X
          </button>
        </span>
      ))}
    </div>
  );
}
