import Image from "next/image";
import Link from "next/link";
import { SearchBox } from "@/components/SearchBox";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { formatPkr, getRetailers, searchProducts, type SearchResult } from "@/lib/api";

type Props = {
  searchParams: Promise<{
    q?: string;
    store?: string;
    stock?: string;
  }>;
};

function filterResultsByStock(
  items: SearchResult[],
  keep: (availability: string) => boolean,
): SearchResult[] {
  return items.flatMap((item) => {
    const offers = (item.offers || []).filter((o) => keep(o.availability));
    if (!offers.length) return [];
    const cheapestOffer = [...offers].sort((a, b) => a.price - b.price)[0];
    const next: SearchResult = {
      ...item,
      offers,
      store_count: offers.length,
      cheapest: {
        retailer_id: cheapestOffer.retailer_id,
        retailer_name: cheapestOffer.retailer_name,
        price: cheapestOffer.price,
        availability: cheapestOffer.availability,
        url: cheapestOffer.url,
      },
    };
    return [next];
  });
}

function ProductCard({ item }: { item: SearchResult }) {
  const offers = item.offers || [];
  const href = item.variant_id ? `/product/${item.variant_id}` : item.cheapest.url;

  return (
    <article className="panel rounded-2xl p-4">
      <div className="grid gap-4 md:grid-cols-[110px_1fr_auto]">
        <Link href={href} className="relative mx-auto h-28 w-28 overflow-hidden rounded-xl bg-white md:mx-0">
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
        </Link>
        <div>
          <Link href={href}>
            <h2 className="text-xl">
              {[item.brand, item.name].filter(Boolean).join(" ")}
            </h2>
          </Link>
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

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  const q = (params.q || "").trim();
  const store = params.store || undefined;
  const stock =
    params.stock === "in" ? true : params.stock === "out" ? false : undefined;

  let results: Awaited<ReturnType<typeof searchProducts>> | null = null;
  let error: string | null = null;
  try {
    if (q) {
      results = await searchProducts(q, { store, inStock: stock });
    }
  } catch (err) {
    error = err instanceof Error ? err.message : "Search failed";
  }

  const retailers = await getRetailers().catch(() => ({ retailers: [] }));
  let flat = results?.all_store_prices || [];
  let productResults = results?.results || [];

  // Harden stock filter in the UI so OOS rows never leak through.
  if (stock === true) {
    flat = flat.filter((o) => o.availability === "in_stock");
    productResults = filterResultsByStock(
      productResults,
      (availability) => availability === "in_stock",
    );
  } else if (stock === false) {
    flat = flat.filter((o) => o.availability !== "in_stock");
    productResults = filterResultsByStock(
      productResults,
      (availability) => availability !== "in_stock",
    );
  }

  return (
    <div className="site-shell">
      <div className="mb-8">
        <SearchBox initialQuery={q} size="compact" />
      </div>

      {!q ? (
        <p className="text-[var(--ink-soft)]">Enter a product to compare prices.</p>
      ) : (
        <>
          <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h1 className="brand-mark text-4xl text-[var(--accent-deep)]">Search results</h1>
              <p className="mt-1 text-[var(--ink-soft)]">
                for &ldquo;{q}&rdquo;
                {results ? ` · ${productResults.length} products` : ""}
                {flat.length ? ` · ${flat.length} store prices` : ""}
                {results?.stores_queried?.length
                  ? ` · checked ${results.stores_queried
                      .map(
                        (id) =>
                          retailers.retailers.find((r) => r.id === id)?.name ||
                          id,
                      )
                      .join(", ")}`
                  : ""}
              </p>
            </div>
            <form className="panel flex flex-wrap gap-3 rounded-2xl p-3">
              <input type="hidden" name="q" value={q} />
              <label className="text-sm">
                Store
                <select
                  name="store"
                  defaultValue={store || ""}
                  className="ml-2 rounded-lg border border-[var(--line)] bg-transparent px-2 py-1"
                >
                  <option value="">All (live)</option>
                  {retailers.retailers.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Stock
                <select
                  name="stock"
                  defaultValue={params.stock || ""}
                  className="ml-2 rounded-lg border border-[var(--line)] bg-transparent px-2 py-1"
                >
                  <option value="">Any</option>
                  <option value="in">In stock</option>
                  <option value="out">Out of stock</option>
                </select>
              </label>
              <button
                type="submit"
                className="btn-accent rounded-lg px-3 py-1 text-sm"
              >
                Apply
              </button>
            </form>
          </div>

          {error ? (
            <p className="rounded-2xl border border-[var(--danger)] bg-white/70 px-4 py-3 text-[var(--danger)]">
              {error}. Is the API running on port 8020?
            </p>
          ) : null}

          {flat.length > 0 ? (
            <section className="panel mb-8 overflow-x-auto rounded-2xl">
              <div className="border-b border-[var(--line)] px-4 py-3">
                <h2 className="brand-mark text-2xl">All store prices</h2>
                <p className="text-sm text-[var(--ink-soft)]">
                  Every matching offer from Pakistani stores, cheapest first.
                </p>
              </div>
              <table className="min-w-full text-left">
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
                        {row.availability === "in_stock" ? "In stock" : "Out of stock"}
                      </td>
                      <td className="px-4 py-3">
                        <a
                          href={row.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-[var(--accent)] underline"
                        >
                          Buy
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          ) : null}

          <div className="grid gap-4">
            <h2 className="brand-mark text-2xl">By product</h2>
            {productResults.map((item, idx) => (
              <ProductCard
                key={`${item.variant_id || item.name}-${item.size_label}-${idx}`}
                item={item}
              />
            ))}
            {results && productResults.length === 0 ? (
              <p className="text-[var(--ink-soft)]">
                No products found across live stores. Try &ldquo;lays&rdquo; or
                &ldquo;brite&rdquo;.
              </p>
            ) : null}
          </div>
        </>
      )}
    </div>
  );
}
