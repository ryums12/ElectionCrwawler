export const DEFAULT_PARTY_COLOR = "#6B7280";

export const PARTY_COLORS: Record<string, string> = {
  "더불어민주당": "#003B96",
  "민주당": "#003B96",
  "국민의힘": "#E61E2B",
  "조국혁신당": "#0073CF",
  "개혁신당": "#FF7210",
  "진보당": "#E60020",
  "기본소득당": "#82C8B4",
  "사회민주당": "#F58400",
  "정의당": "#FFCC00",
  "녹색당": "#62BB46",
  "무소속": "#6B7280",
};

export const getPartyColor = (partyName: string): string => {
  const normalizedName = partyName.trim();

  return PARTY_COLORS[normalizedName] ?? DEFAULT_PARTY_COLOR;
};

export const getReadableTextColor = (backgroundColor: string): "#000000" | "#FFFFFF" => {
  const normalizedColor = backgroundColor.trim().replace("#", "");

  if (!/^[0-9a-fA-F]{6}$/.test(normalizedColor)) {
    return "#FFFFFF";
  }

  const red = Number.parseInt(normalizedColor.slice(0, 2), 16);
  const green = Number.parseInt(normalizedColor.slice(2, 4), 16);
  const blue = Number.parseInt(normalizedColor.slice(4, 6), 16);
  const luminance = (0.299 * red + 0.587 * green + 0.114 * blue) / 255;

  return luminance > 0.58 ? "#000000" : "#FFFFFF";
};
