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
        placeholder="원하는 내용을 검색하세요."
        className="h-14 w-full rounded-lg border border-line bg-slate-950/70 px-5 text-base text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-violet-400 focus:ring-4 focus:ring-violet-500/20"
      />
    </label>
  );
}
