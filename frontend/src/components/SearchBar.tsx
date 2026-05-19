"use client";

type SearchBarProps = {
  value: string;
  onChange: (value: string) => void;
};

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <label className="block">
      <span className="sr-only">Search election news</span>
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search title, summary, party, region, person, or keyword"
        className="h-14 w-full rounded-lg border border-slate-300 bg-white px-5 text-base text-slate-950 outline-none transition placeholder:text-slate-500 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/15 dark:border-line dark:bg-slate-950/70 dark:text-slate-100 dark:focus:border-violet-400 dark:focus:ring-violet-500/20"
      />
    </label>
  );
}
