import path from "node:path";
import { NextRequest, NextResponse } from "next/server";
import { loadEnvConfig } from "@next/env";
import { Pool } from "pg";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type NewsRow = {
  id: number;
  title: string | null;
  summary: string | null;
  description: string | null;
  source_name: string | null;
  published_at: Date | string | null;
  created_at: Date | string | null;
  fetched_at: Date | string | null;
  original_url: string | null;
  naver_url: string | null;
  canonical_url: string | null;
  parties: unknown;
  regions: unknown;
  people: unknown;
  main_keywords: unknown;
};

const MAX_LIMIT = 50;
const DEFAULT_LIMIT = 10;
const SEARCH_COLUMNS = [
  "title",
  "description",
  "summary",
  "main_keywords",
  "parties",
  "regions",
  "people",
  "source_name",
  "search_keyword",
];

export async function GET(request: NextRequest) {
  try {
    loadRootEnv();

    const { searchParams } = request.nextUrl;
    const q = searchParams.get("q")?.trim() ?? "";
    const parties = getAllParams(searchParams, "party", "parties");
    const regions = getAllParams(searchParams, "region", "regions");
    const people = getAllParams(searchParams, "person", "people");
    const limit = parseBoundedInt(searchParams.get("limit"), DEFAULT_LIMIT, 1, MAX_LIMIT);
    const page = parseBoundedInt(searchParams.get("page"), 1, 1, Number.MAX_SAFE_INTEGER);
    const offset = searchParams.has("offset")
      ? parseBoundedInt(searchParams.get("offset"), 0, 0, Number.MAX_SAFE_INTEGER)
      : (page - 1) * limit;

    const pool = new Pool({
      host: getRequiredEnv("DB_HOST"),
      port: parseBoundedInt(process.env.DB_PORT, 6543, 1, 65535),
      database: getRequiredEnv("DB_NAME"),
      user: getRequiredEnv("DB_USER"),
      password: getRequiredEnv("DB_PASSWORD"),
      ssl: getDbSslConfig(),
      connectionTimeoutMillis: 8000,
      idleTimeoutMillis: 1000,
      max: 1,
    });

    try {
      const { whereSql, values } = buildWhereClause({ q, parties, regions, people });
      const result = await pool.query<NewsRow>(
        `
          SELECT
            id,
            title,
            summary,
            description,
            source_name,
            published_at,
            created_at,
            fetched_at,
            original_url,
            naver_url,
            canonical_url,
            parties,
            regions,
            people,
            main_keywords
          FROM articles
          ${whereSql}
          ORDER BY COALESCE(published_at, created_at, fetched_at) DESC, id DESC
          LIMIT $${values.length + 1} OFFSET $${values.length + 2}
        `,
        [...values, limit + 1, offset],
      );

      const newsRows = result.rows;
      const visibleRows = newsRows.slice(0, limit);
      const items = visibleRows.map(normalizeRow);

      return NextResponse.json({
        items,
        nextOffset: offset + items.length,
        hasMore: newsRows.length > limit,
      });
    } finally {
      await pool.end();
    }
  } catch (error) {
    logApiError(error);
    return new NextResponse("News data is temporarily unavailable. Please try again later.", { status: 503 });
  }
}

const buildWhereClause = ({
  q,
  parties,
  regions,
  people,
}: {
  q: string;
  parties: string[];
  regions: string[];
  people: string[];
}) => {
  const clauses: string[] = [];
  const values: Array<string | number> = [];

  if (q) {
    const searchClauses = SEARCH_COLUMNS.map((column) => {
      values.push(`%${q}%`);
      return `${jsonSearchExpression(column)} ILIKE $${values.length}`;
    });
    clauses.push(`(${searchClauses.join(" OR ")})`);
  }

  addTextFilter(clauses, values, "parties", parties);
  addTextFilter(clauses, values, "regions", regions);
  addTextFilter(clauses, values, "people", people);

  return {
    whereSql: clauses.length > 0 ? `WHERE ${clauses.join(" AND ")}` : "",
    values,
  };
};

const addTextFilter = (
  clauses: string[],
  values: Array<string | number>,
  column: "parties" | "regions" | "people",
  selectedValues: string[],
) => {
  if (selectedValues.length === 0) {
    return;
  }

  const filterClauses = selectedValues.map((value) => {
    values.push(`%${value}%`);
    return `${column}::text ILIKE $${values.length}`;
  });
  clauses.push(`(${filterClauses.join(" OR ")})`);
};

const normalizeRow = (row: NewsRow) => {
  const publishedAt = toIsoString(row.published_at ?? row.created_at ?? row.fetched_at);
  const description = row.description ?? "";
  const summary = row.summary || description;

  return {
    id: row.id,
    title: row.title || "Untitled article",
    summary,
    description,
    sourceName: row.source_name ?? "",
    publishedAt,
    originalUrl: row.original_url || row.canonical_url || row.naver_url || "",
    naverUrl: row.naver_url,
    parties: splitList(row.parties),
    regions: splitList(row.regions),
    people: splitList(row.people),
    keywords: splitList(row.main_keywords),
  };
};

const splitList = (value: unknown) => {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.map(String).map((item) => item.trim()).filter(Boolean);
  }

  const trimmed = String(value).trim();
  if (!trimmed) {
    return [];
  }

  try {
    const parsed = JSON.parse(trimmed);
    if (Array.isArray(parsed)) {
      return parsed.map(String).map((item) => item.trim()).filter(Boolean);
    }
  } catch {
    // Fall through to delimiter splitting for plain text storage.
  }

  return trimmed
    .split(/[,;|/\n\r]+/)
    .map((item) => item.trim())
    .filter(Boolean);
};

const getAllParams = (searchParams: URLSearchParams, singular: string, plural: string) =>
  [...searchParams.getAll(singular), ...searchParams.getAll(plural)]
    .flatMap((value) => value.split(","))
    .map((value) => value.trim())
    .filter(Boolean);

const parseBoundedInt = (value: string | null | undefined, fallback: number, min: number, max: number) => {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }

  return Math.min(Math.max(parsed, min), max);
};

const toIsoString = (value: Date | string | null) => {
  if (!value) {
    return null;
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
};

const getRequiredEnv = (name: string) => {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Missing required database environment variable: ${name}. ` +
        "Database settings must be configured explicitly; the app no longer falls back to localhost.",
    );
  }

  return value;
};

const loadRootEnv = () => {
  loadEnvConfig(path.resolve(process.cwd(), ".."));
};

const jsonSearchExpression = (column: string) => {
  if (["main_keywords", "parties", "regions", "people"].includes(column)) {
    return `${column}::text`;
  }

  return `COALESCE(${column}, '')`;
};

const getDbSslConfig = () => {
  const value = process.env.DB_SSL?.trim().toLowerCase();
  if (value && ["0", "false", "no", "disable"].includes(value)) {
    return false;
  }

  return { rejectUnauthorized: false };
};

const logApiError = (error: unknown) => {
  if (!(error instanceof Error)) {
    console.error("News API request failed.");
    return;
  }

  const code = "code" in error ? String(error.code) : "unknown";
  console.error(`News API request failed: ${error.name} (${code})`);
};
