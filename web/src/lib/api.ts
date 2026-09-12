const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://pricewise-api-dauj.onrender.com"
    : "http://127.0.0.1:8000");

export type Freshness = {
  level: "live" | "today" | "stale" | "unknown";
  label: string;
  checked_at: string | null;
};

export type UnitPrice = {
  amount: number;
  unit: string;
} | null;

export type StoreOffer = {
  retailer_id: string;
  retailer_name: string;
  product_name: string;
  price: number;
  compare_at_price?: number | null;
  availability: string;
  url: string;
  image_url?: string | null;
  size_label?: string;
  unit_price: UnitPrice;
  freshness: Freshness;
  variant_id?: number | null;
  source?: string;
};

export type SearchResult = {
  variant_id: number | null;
  product_id?: number;
  brand: string | null;
  name: string;
  size_label: string;
  image_url: string | null;
  store_count: number;
  cheapest: {
    retailer_id: string;
    retailer_name: string;
    price: number;
    availability: string;
    url: string;
  };
  unit_price: UnitPrice;
  freshness: Freshness;
  offers?: StoreOffer[];
  score?: number;
};

export type PriceRow = {
  retailer_id: string;
  retailer_name: string;
  product_name: string;
  price: number;
  compare_at_price: number | null;
  discount: number | null;
  availability: string;
  url: string;
  image_url: string | null;
  match_confidence: number | null;
  unit_price: UnitPrice;
  freshness: Freshness;
};

export type Comparison = {
  variant: {
    id: number;
    product_id: number;
    brand: string | null;
    name: string;
    size_label: string;
    pack_count: number;
    barcode: string | null;
    image_url: string | null;
  };
  prices: PriceRow[];
  cheapest: PriceRow | null;
  savings: {
    amount: number;
    from_store: string;
    to_store: string;
  } | null;
  store_count: number;
};

export type Retailer = {
  id: string;
  name: string;
  slug: string;
  website_url: string;
  status: string;
  platform: string | null;
  last_successful_sync: string | null;
};

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 0 },
    cache: "no-store",
    signal: AbortSignal.timeout(55_000),
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function formatPkr(amount: number): string {
  return `Rs. ${amount.toLocaleString("en-PK", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

export async function searchProducts(
  q: string,
  opts?: { store?: string; inStock?: boolean; live?: boolean },
) {
  const params = new URLSearchParams({ q });
  // Live multi-store by default; backend enforces a short scrape budget.
  params.set("live", opts?.live === false ? "false" : "true");
  if (opts?.store) params.set("store", opts.store);
  if (opts?.inStock === true) params.set("in_stock", "true");
  if (opts?.inStock === false) params.set("in_stock", "false");
  const res = await fetch(`${API_BASE}/api/search?${params.toString()}`, {
    next: { revalidate: 0 },
    cache: "no-store",
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) {
    throw new Error(`API /api/search failed (${res.status})`);
  }
  return res.json() as Promise<{
    query: string;
    mode?: string;
    parsed: { name: string; size_label: string | null; pack_count: number | null };
    results: SearchResult[];
    all_store_prices?: StoreOffer[];
    stores_queried?: string[];
  }>;
}

export async function suggestProducts(q: string) {
  const params = new URLSearchParams({ q });
  return apiGet<{
    suggestions: { variant_id: number; label: string; size_label: string }[];
  }>(`/api/search/suggest?${params.toString()}`);
}

export async function getComparison(variantId: number, sort = "cheapest") {
  return apiGet<Comparison>(`/api/variants/${variantId}?sort=${sort}`);
}

export async function getRetailers() {
  return apiGet<{ retailers: Retailer[] }>("/api/retailers");
}

export async function getAdminStats() {
  return apiGet<{
    products: number;
    variants: number;
    retailer_products: number;
    prices: number;
    matching_reviews: number;
    jobs_error: number;
    updated_today: number;
  }>("/api/admin/stats");
}

export async function getAdminJobs() {
  return apiGet<{
    jobs: {
      id: number;
      retailer_id: string;
      status: string;
      items_upserted: number;
      error: string | null;
      started_at: string | null;
      finished_at: string | null;
    }[];
  }>("/api/admin/jobs");
}

export { API_BASE };
