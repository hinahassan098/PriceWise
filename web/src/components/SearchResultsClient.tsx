"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CityPicker, normalizeCityParam, readStoredCity, writeStoredCity } from "@/components/CityPicker";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import {
  API_BASE,
  formatPkr,
  searchProducts,
  type Retailer,
  type SearchResult,
  type StoreOffer,
} from "@/lib/api";

type SearchPayload = Awaited<ReturnType<typeof searchProducts>>;

type Props = {
  q: string;
  store?: string;
  stock?: string;
  city?: string;
};

function filterResultsByStock(
  items: SearchResult[],
  keep: (availability: string) => boolean,
): SearchResult[] {
  return items.flatMap((item) => {
    const offers = (item.offers || []).filter((o) => keep(o.availability));
    if (!offers.length) return [];
    const cheapestOffer = [...offers].sort(
      (a, b) => (a.price ?? 1e12) - (b.price ?? 1e12),
    )[0];
    const next: SearchResult = {
      ...item,
      offers,
      store_count: offers.length,
      cheapest: {
        retailer_id: cheapestOffer.retailer_id,
        retailer_name: cheapestOffer.retailer_name,
        price: cheapestOffer.price ?? 0,
        availability: cheapestOffer.availability,
        url: cheapestOffer.url,
      },
    };
    return [next];
  });
}

function ProductCard({ item }: { item: SearchResult }) {
  const offers = item.offers || [];
  const internalHref = item.variant_id ? `/product/${item.variant_id}` : null;
  const externalHref = item.cheapest.url;
  const TitleWrap = internalHref
    ? ({ children }: { children: ReactNode }) => (
        <Link href={internalHref}>{children}</Link>
      )
    : ({ children }: { children: ReactNode }) => (
        <a href={externalHref} target="_blank" rel="noreferrer">
          {children}
        </a>
      );

  return (
    <article className="panel result-panel rounded-2xl p-5">
      <div className="grid gap-4 md:grid-cols-[110px_1fr_auto]">
        <TitleWrap>
          <span className="relative mx-auto block h-28 w-28 overflow-hidden rounded-2xl bg-gradient-to-b from-white to-[rgba(243,197,211,0.25)] md:mx-0">
            {item.image_url ? (
              <Image
                src={item.image_url}
                alt={item.name}
                fill
                className="object-contain p-2"
                sizes="112px"
                unoptimized
              />
            ) : null}
          </span>
        </TitleWrap>
        <div>
          <TitleWrap>
            <h2 className="text-xl">
              {[item.brand, item.name].filter(Boolean).join(" ")}
            </h2>
          </TitleWrap>
          <p className="mt-1 text-[var(--ink-soft)]">{item.size_label}</p>
          <p className="mt-2 text-sm">
            {item.store_count} {item.store_count === 1 ? "store" : "stores"} compared
          </p>
        </div>
        <div className="text-right">
          <p className="text-sm text-[var(--accent)]">Cheapest</p>
          <p className="text-2xl font-medium">{formatPkr(item.cheapest.price)}</p>
          <p className="text-sm text-[var(--ink-soft)]">
            <a
              href={item.cheapest.url}
              target="_blank"
              rel="noreferrer"
              className="underline decoration-[var(--line)] underline-offset-2 hover:text-[var(--accent)]"
            >
              {item.cheapest.retailer_name}
            </a>
          </p>
        </div>
      </div>

      {offers.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-[var(--line)]">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-[var(--line)] text-[var(--ink-soft)]">
              <tr>
                <th className="px-3 py-2 font-normal">Store</th>
                <th className="px-3 py-2 font-normal">Price</th>
                <th className="px-3 py-2 font-normal">Stock</th>
                <th className="px-3 py-2 font-normal">Updated</th>
                <th className="px-3 py-2 font-normal" />
              </tr>
            </thead>
            <tbody>
              {offers.map((offer) => {
                const isCheapest =
                  offer.retailer_id === item.cheapest.retailer_id &&
                  offer.price === item.cheapest.price;
                return (
                  <tr
                    key={`${offer.retailer_id}-${offer.url}`}
                    className={`border-b border-[var(--line)] last:border-b-0 ${
                      isCheapest ? "cheapest-row" : ""
                    }`}
                  >
                    <td className="px-3 py-2 font-medium">
                      <a
                        href={offer.url}
                        target="_blank"
                        rel="noreferrer"
                        className="underline decoration-[var(--line)] underline-offset-2 hover:text-[var(--accent)]"
                      >
                        {offer.retailer_name}
                      </a>
                      {isCheapest ? (
                        <span className="ml-2 text-xs text-[var(--accent)]">Cheapest</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">{formatPkr(offer.price)}</td>
                    <td className="px-3 py-2">
                      {offer.availability === "in_stock" ? "In stock" : "Out of stock"}
                    </td>
                    <td className="px-3 py-2">
                      <FreshnessBadge freshness={offer.freshness} />
                    </td>
                    <td className="px-3 py-2">
                      <a
                        href={offer.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[var(--accent)] underline"
                      >
                        Buy
                      </a>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </article>
  );
}

async function fetchWithRetry(q: string, store?: string, inStock?: boolean, city?: string) {
  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      // Wake API on first failure (Render free tier cold start).
      if (attempt > 0) {
        await fetch(`${API_BASE}/api/health`, { cache: "no-store" }).catch(() => null);
        await new Promise((r) => setTimeout(r, 1500 * attempt));
      }
      return await searchProducts(q, { store, city, inStock, live: true });
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("Search failed");
}

export function SearchResultsClient({ q, store, stock, city }: Props) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchPayload | null>(null);
  const [retailers, setRetailers] = useState<Retailer[]>([]);

  const inStock =
    stock === "in" ? true : stock === "out" ? false : undefined;
  const cityNorm = normalizeCityParam(city || "all");
  const cityFilter = cityNorm !== "all" ? cityNorm : undefined;

  // Keep URL in sync with stored city when landing without ?city=
  useEffect(() => {
    if (city) {
      writeStoredCity(normalizeCityParam(city));
      return;
    }
    const stored = normalizeCityParam(readStoredCity());
    if (stored === "all") return;
    const params = new URLSearchParams();
    params.set("q", q);
    params.set("city", stored);
    if (store) params.set("store", store);
    if (stock) params.set("stock", stock);
    router.replace(`/search?${params.toString()}`);
  }, [city, q, store, stock, router]);

  function pushFilters(next: { store?: string; stock?: string; city?: string }) {
    const params = new URLSearchParams();
    params.set("q", q);
    const nextCity = normalizeCityParam(
      next.city !== undefined ? next.city : cityNorm,
    );
    const nextStore = next.store !== undefined ? next.store : store || "";
    const nextStock = next.stock !== undefined ? next.stock : stock || "";
    if (nextCity && nextCity !== "all") params.set("city", nextCity);
    if (nextStore) params.set("store", nextStore);
    if (nextStock) params.set("stock", nextStock);
    router.push(`/search?${params.toString()}`);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setResults(null);

    (async () => {
      try {
        const retailersUrl = cityFilter
          ? `${API_BASE}/api/retailers?city=${encodeURIComponent(cityFilter)}`
          : `${API_BASE}/api/retailers`;
        const [data, retailerPayload] = await Promise.all([
          fetchWithRetry(q, store, inStock, cityFilter),
          fetch(retailersUrl, { cache: "no-store" })
            .then((r) => (r.ok ? r.json() : { retailers: [] }))
            .catch(() => ({ retailers: [] as Retailer[] })),
        ]);
        if (cancelled) return;
        const list: Retailer[] = retailerPayload.retailers || [];
        setResults(data);
        setRetailers(list);
        // Drop store filter if it isn't available in this city.
        if (store && list.length > 0 && !list.some((r) => r.id === store)) {
          const params = new URLSearchParams();
          params.set("q", q);
          if (cityFilter) params.set("city", cityFilter);
          if (stock) params.set("stock", stock);
          router.replace(`/search?${params.toString()}`);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Search failed");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [q, store, inStock, cityFilter, stock, router]);

  const { flat, productResults } = useMemo(() => {
    let nextFlat: StoreOffer[] = results?.all_store_prices || [];
    let nextProducts: SearchResult[] = results?.results || [];
    if (inStock === true) {
      nextFlat = nextFlat.filter((o) => o.availability === "in_stock");
      nextProducts = filterResultsByStock(
        nextProducts,
        (availability) => availability === "in_stock",
      );
    } else if (inStock === false) {
      nextFlat = nextFlat.filter((o) => o.availability !== "in_stock");
      nextProducts = filterResultsByStock(
        nextProducts,
        (availability) => availability !== "in_stock",
      );
    }
    return { flat: nextFlat, productResults: nextProducts };
  }, [results, inStock]);

  return (
    <>
      <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="brand-mark text-4xl text-[var(--accent-deep)] md:text-5xl">
            Search results
          </h1>
          <p className="mt-1 text-[var(--ink-soft)]">
            for &ldquo;{q}&rdquo;
            {cityFilter ? ` · ${cityFilter}` : " · All Pakistan"}
            {store
              ? ` · ${retailers.find((r) => r.id === store)?.name || store}`
              : " · all stores"}
            {loading ? " · searching live stores…" : null}
            {!loading && results ? ` · ${productResults.length} products` : ""}
            {!loading && flat.length ? ` · ${flat.length} store prices` : ""}
            {!loading && results?.stores_queried?.length
              ? ` · checked ${results.stores_queried
                  .map(
                    (id) => retailers.find((r) => r.id === id)?.name || id,
                  )
                  .join(", ")}`
              : ""}
          </p>
          {!loading && results?.store_errors
            ? (() => {
                const hard = Object.entries(results.store_errors).filter(
                  ([, msg]) =>
                    /timed out|blocked|error|fail|exception/i.test(msg) &&
                    !/linked to store/i.test(msg),
                );
                if (!hard.length) return null;
                return (
                  <p className="mt-1 text-sm text-[var(--ink-soft)]">
                    Some stores slow or blocked:{" "}
                    {hard
                      .map(
                        ([id, msg]) =>
                          `${retailers.find((r) => r.id === id)?.name || id} (${msg})`,
                      )
                      .join(" · ")}
                  </p>
                );
              })()
            : null}
        </div>
        <div className="panel filter-bar flex flex-wrap items-end gap-3 rounded-2xl p-4">
          <CityPicker value={cityNorm} syncUrl variant="default" />
          <label className="text-sm">
            Store
            <select
              value={store && retailers.some((r) => r.id === store) ? store : ""}
              onChange={(e) => pushFilters({ store: e.target.value })}
              className="ml-2 rounded-lg border border-[var(--line)] bg-transparent px-2 py-1"
              aria-label="Filter by store"
            >
              <option value="">All (live)</option>
              {retailers.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Stock
            <select
              value={stock || ""}
              onChange={(e) => pushFilters({ stock: e.target.value })}
              className="ml-2 rounded-lg border border-[var(--line)] bg-transparent px-2 py-1"
              aria-label="Filter by stock"
            >
              <option value="">Any</option>
              <option value="in">In stock</option>
              <option value="out">Out of stock</option>
            </select>
          </label>
        </div>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-[var(--line)] bg-white/70 px-4 py-6 text-[var(--ink-soft)]">
          Comparing prices across stores{cityFilter ? ` in ${cityFilter}` : ""}
          {store ? ` · ${retailers.find((r) => r.id === store)?.name || store}` : ""}
          … this can take up to 20 seconds on first load.
        </p>
      ) : null}

      {error ? (
        <p className="rounded-2xl border border-[var(--danger)] bg-white/70 px-4 py-3 text-[var(--danger)]">
          {error}. Retrying after the API wakes up usually helps — refresh once.
        </p>
      ) : null}

      {!loading && results?.store_links?.length ? (
        <div className="panel filter-bar mb-6 flex flex-wrap items-center gap-2 rounded-2xl p-4">
          <span className="section-kicker mr-1">Search on</span>
          {results.store_links
            .filter((l) => ["naheed", "carrefour", "imtiaz"].includes(l.retailer_id))
            .map((link) => (
              <a
                key={link.retailer_id}
                href={link.url}
                target="_blank"
                rel="noreferrer"
                className="rounded-xl border border-[var(--line)] bg-white/80 px-3 py-1.5 text-sm font-medium text-[var(--accent-deep)] transition hover:border-[var(--accent-soft)] hover:bg-[rgba(243,197,211,0.35)]"
              >
                {link.retailer_name} ↗
              </a>
            ))}
        </div>
      ) : null}

      {!loading && results?.mode === "empty_city_store" ? (
        <p className="rounded-2xl border border-[var(--line)] bg-white/70 px-4 py-4 text-[var(--ink-soft)]">
          {store || "That store"} is not available in {cityFilter || "this city"}. Pick another
          store or switch city.
        </p>
      ) : null}

      {!loading && flat.length > 0 ? (
        <section className="panel result-panel mb-8 overflow-x-auto rounded-2xl">
          <div className="border-b border-[var(--line)] px-5 py-4">
            <p className="section-kicker">Live compare</p>
            <h2 className="brand-mark mt-1 text-2xl md:text-3xl">All store prices</h2>
            <p className="mt-1 text-sm text-[var(--ink-soft)]">
              Every matching offer from{" "}
              {cityFilter ? `${cityFilter} stores` : "Pakistani stores"}, cheapest first.
            </p>
          </div>
          <table className="price-table min-w-full text-left">
            <thead className="border-b border-[var(--line)] text-sm text-[var(--ink-soft)]">
              <tr>
                <th className="px-4 py-3 font-normal">Store</th>
                <th className="px-4 py-3 font-normal">Product</th>
                <th className="px-4 py-3 font-normal">Size</th>
                <th className="px-4 py-3 font-normal">Price</th>
                <th className="px-4 py-3 font-normal">Stock</th>
                <th className="px-4 py-3 font-normal" />
              </tr>
            </thead>
            <tbody>
              {flat.slice(0, 40).map((row, idx) => (
                <tr
                  key={`${row.retailer_id}-${row.url}-${idx}`}
                  className="border-b border-[var(--line)] last:border-b-0"
                >
                  <td className="px-4 py-3 font-medium">
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-[var(--line)] underline-offset-2 hover:text-[var(--accent)]"
                    >
                      {row.retailer_name}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-sm">{row.product_name}</td>
                  <td className="px-4 py-3 text-sm text-[var(--ink-soft)]">
                    {row.size_label || "—"}
                  </td>
                  <td className="px-4 py-3">{formatPkr(row.price)}</td>
                  <td className="px-4 py-3 text-sm">
                    {row.source === "store_link"
                      ? "Open store"
                      : row.availability === "in_stock"
                        ? "In stock"
                        : "Out of stock"}
                  </td>
                  <td className="px-4 py-3">
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[var(--accent)] underline"
                    >
                      {row.source === "store_link" ? "Open" : "Buy"}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {!loading ? (
        <div className="grid gap-4" style={{ animation: "rise-in 0.65s ease-out 0.1s both" }}>
          <div>
            <p className="section-kicker">Grouped</p>
            <h2 className="brand-mark mt-1 text-2xl md:text-3xl">By product</h2>
          </div>
          {productResults.map((item, idx) => (
            <ProductCard
              key={`${item.variant_id || item.name}-${item.size_label}-${idx}`}
              item={item}
            />
          ))}
          {results && productResults.length === 0 && results.mode !== "empty_city_store" ? (
            <p className="text-[var(--ink-soft)]">
              No products found across live stores
              {cityFilter ? ` for ${cityFilter}` : ""}
              {store ? ` at ${retailers.find((r) => r.id === store)?.name || store}` : ""}. Try
              another brand, spelling, city, or store.
            </p>
          ) : null}
        </div>
      ) : null}
    </>
  );
}
