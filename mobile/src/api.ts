const API_BASE = "https://pricewise-api-dauj.onrender.com";

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
  availability: string;
  url: string;
  image_url?: string | null;
  size_label?: string;
  unit_price: UnitPrice;
  freshness: Freshness;
};

export type SearchResult = {
  variant_id: number | null;
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
};

export type SearchResponse = {
  query: string;
  mode?: string;
  results: SearchResult[];
  all_store_prices?: StoreOffer[];
  stores_queried?: string[];
};

export function formatPkr(amount: number): string {
  return `Rs. ${amount.toLocaleString("en-PK", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
}

async function apiGet<T>(path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 45000);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      throw new Error(`API ${path} failed (${res.status})`);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export async function wakeApi(): Promise<void> {
  try {
    await apiGet("/api/health");
  } catch {
    // Cold starts are expected on Render free tier.
  }
}

export async function searchProducts(q: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, live: "true" });
  return apiGet<SearchResponse>(`/api/search?${params.toString()}`);
}

export { API_BASE };
