export type FilterType = "parties" | "regions" | "people";

export type Article = {
  id: string;
  title: string;
  content: string;
  summary: string;
  originalUrl: string;
  parties: string[];
  regions: string[];
  people: string[];
};

export type ArticleSearchParams = {
  query: string;
  parties: string[];
  regions: string[];
  people: string[];
  page: number;
  limit: number;
};

export type ArticleSearchResult = {
  articles: Article[];
  hasMore: boolean;
};

const partyPool = ["Democratic Party", "People Power Party", "Justice Party", "Reform Party"];
const regionPool = ["Seoul", "Busan", "Incheon", "Daegu", "Gwangju", "Daejeon"];
const peoplePool = ["Hong Gil-dong", "Kim Hana", "Lee Min-jun", "Park Seo-yeon", "Choi Ji-ho"];

const mockArticles: Article[] = Array.from({ length: 48 }, (_, index) => {
  const party = partyPool[index % partyPool.length];
  const secondParty = partyPool[(index + 1) % partyPool.length];
  const region = regionPool[index % regionPool.length];
  const person = peoplePool[index % peoplePool.length];
  const issue = ["housing", "transportation", "youth jobs", "public safety", "climate policy", "local finance"][
    index % 6
  ];

  return {
    id: `mock-${index + 1}`,
    title: `${region} election race focuses on ${issue} pledge #${index + 1}`,
    content: `${party} and ${secondParty} candidates discussed ${issue} in ${region}. ${person} emphasized practical local commitments, voter outreach, and transparent budget planning during the campaign stop.`,
    summary: `${person} outlined a ${region} campaign message centered on ${issue}. The article compares responses from ${party} and ${secondParty}, highlighting where local voters may see concrete policy differences before election day.`,
    originalUrl: `https://example.com/election-news/${index + 1}`,
    parties: index % 3 === 0 ? [party, secondParty] : [party],
    regions: index % 4 === 0 ? [region, regionPool[(index + 2) % regionPool.length]] : [region],
    people: index % 5 === 0 ? [person, peoplePool[(index + 2) % peoplePool.length]] : [person],
  };
});

const containsText = (value: string, query: string) => value.toLowerCase().includes(query);

const containsAny = (values: string[], selected: string[]) => {
  if (selected.length === 0) {
    return true;
  }

  return selected.some((filterValue) => values.includes(filterValue));
};

const matchesGlobalQuery = (article: Article, query: string) => {
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return true;
  }

  return [
    article.title,
    article.content,
    article.summary,
    ...article.parties,
    ...article.regions,
    ...article.people,
  ].some((field) => containsText(field, normalizedQuery));
};

const matchesStructuredFilters = (article: Article, params: ArticleSearchParams) =>
  containsAny(article.parties, params.parties) &&
  containsAny(article.regions, params.regions) &&
  containsAny(article.people, params.people);

const fetchFromApi = async (params: ArticleSearchParams): Promise<ArticleSearchResult> => {
  const apiUrl = process.env.NEXT_PUBLIC_ARTICLES_API_URL;

  if (!apiUrl) {
    throw new Error("NEXT_PUBLIC_ARTICLES_API_URL is not configured.");
  }

  const searchParams = new URLSearchParams();
  searchParams.set("query", params.query);
  searchParams.set("page", String(params.page));
  searchParams.set("limit", String(params.limit));
  params.parties.forEach((party) => searchParams.append("parties", party));
  params.regions.forEach((region) => searchParams.append("regions", region));
  params.people.forEach((person) => searchParams.append("people", person));

  const response = await fetch(`${apiUrl}?${searchParams.toString()}`, {
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Article request failed with status ${response.status}`);
  }

  return response.json();
};

const fetchFromMockData = async (params: ArticleSearchParams): Promise<ArticleSearchResult> => {
  await new Promise((resolve) => window.setTimeout(resolve, 250));

  const filteredArticles = mockArticles.filter(
    (article) => matchesGlobalQuery(article, params.query) && matchesStructuredFilters(article, params),
  );
  const start = (params.page - 1) * params.limit;
  const articles = filteredArticles.slice(start, start + params.limit);

  return {
    articles,
    hasMore: start + params.limit < filteredArticles.length,
  };
};

export const fetchArticles = async (params: ArticleSearchParams): Promise<ArticleSearchResult> => {
  if (process.env.NEXT_PUBLIC_ARTICLES_API_URL) {
    return fetchFromApi(params);
  }

  return fetchFromMockData(params);
};
