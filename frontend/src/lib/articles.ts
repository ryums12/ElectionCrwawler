export type FilterType = "parties" | "regions" | "people";

export type Article = {
  id: number;
  title: string;
  summary: string;
  description: string;
  sourceName: string;
  publishedAt: string | null;
  originalUrl: string;
  naverUrl: string | null;
  parties: string[];
  regions: string[];
  people: string[];
  keywords: string[];
};

export type ArticleSearchParams = {
  query: string;
  parties: string[];
  regions: string[];
  people: string[];
  offset: number;
  limit: number;
};

export type ArticleSearchResult = {
  items: Article[];
  nextOffset: number;
  hasMore: boolean;
};

export const fetchArticles = async (params: ArticleSearchParams): Promise<ArticleSearchResult> => {
  const searchParams = new URLSearchParams();
  const query = params.query.trim();

  if (query) {
    searchParams.set("q", query);
  }

  searchParams.set("limit", String(params.limit));
  searchParams.set("offset", String(params.offset));
  params.parties.forEach((party) => searchParams.append("party", party));
  params.regions.forEach((region) => searchParams.append("region", region));
  params.people.forEach((person) => searchParams.append("person", person));

  const response = await fetch(`/api/news?${searchParams.toString()}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `News request failed with status ${response.status}`);
  }

  return response.json();
};
