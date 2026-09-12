import Image from "next/image";
import Link from "next/link";
import { FreshnessBadge } from "@/components/FreshnessBadge";
import { formatPkr, getComparison } from "@/lib/api";

type Props = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ sort?: string }>;
};

export default async function ProductPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { sort = "cheapest" } = await searchParams;
  const variantId = Number(id);

  let data: Awaited<ReturnType<typeof getComparison>> | null = null;
  let error: string | null = null;
  try {
    data = await getComparison(variantId, sort);
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to load product";
  }

  if (error || !data) {
    return (
      <div className="site-shell">
        <p className="text-[var(--danger)]">{error || "Product not found"}</p>
        <Link href="/" className="mt-4 inline-block underline">
          Back home
        </Link>
      </div>
    );
  }

  const title = [data.variant.brand, data.variant.name]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="site-shell">
      <div className="grid gap-8 md:grid-cols-[220px_1fr]">
        <div className="panel relative mx-auto h-52 w-52 overflow-hidden rounded-3xl bg-white md:mx-0">
          {data.variant.image_url ? (
            <Image
              src={data.variant.image_url}
              alt={title}
              fill
              className="object-contain p-4"
              sizes="208px"
              unoptimized
            />
          ) : null}
        </div>
        <div>
          <p className="text-sm uppercase tracking-[0.18em] text-[var(--ink-soft)]">
            Compare prices
          </p>
          <h1 className="brand-mark mt-2 text-4xl text-[var(--accent-deep)] md:text-5xl">{title}</h1>
          <p className="mt-2 text-lg text-[var(--ink-soft)]">
            {data.variant.size_label}
          </p>
          {data.cheapest ? (
            <div className="panel mt-6 max-w-md rounded-2xl p-5">
              <p className="text-sm text-[var(--accent)]">Cheapest in stock</p>
              <p className="mt-1 text-3xl font-medium">
                <a
                  href={data.cheapest.url}
                  target="_blank"
                  rel="noreferrer"
                  className="underline decoration-[var(--line)] underline-offset-2 hover:text-[var(--accent)]"
                >
                  {data.cheapest.retailer_name}
                </a>{" "}
                — {formatPkr(data.cheapest.price)}
              </p>
              <FreshnessBadge freshness={data.cheapest.freshness} />
              <a
                href={data.cheapest.url}
                target="_blank"
                rel="noreferrer"
                className={`mt-4 inline-block rounded-xl px-4 py-2 btn-accent`}
              >
                View on {data.cheapest.retailer_name}
              </a>
            </div>
          ) : null}
          {data.savings ? (
            <p className="mt-4 text-[var(--ink-soft)]">
              You can save {formatPkr(data.savings.amount)} by buying from{" "}
              {data.savings.to_store} instead of {data.savings.from_store}.
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-10 flex flex-wrap items-center justify-between gap-3">
        <h2 className="brand-mark text-3xl">
          {data.store_count} store{data.store_count === 1 ? "" : "s"}
        </h2>
        <div className="flex flex-wrap gap-2 text-sm">
          {[
            ["cheapest", "Cheapest"],
            ["expensive", "Most expensive"],
            ["store", "Store"],
            ["availability", "Availability"],
          ].map(([value, label]) => (
            <Link
              key={value}
              href={`/product/${variantId}?sort=${value}`}
              className={`rounded-xl border px-3 py-1 ${
                sort === value
                  ? "border-[var(--accent)] bg-[var(--accent)] text-white"
                  : "border-[var(--line)] hover:border-[var(--accent-soft)]"
              }`}
            >
              {label}
            </Link>
          ))}
        </div>
      </div>

      <div className="panel mt-4 overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left">
          <thead className="border-b border-[var(--line)] text-sm text-[var(--ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-normal">Store</th>
              <th className="px-4 py-3 font-normal">Product</th>
              <th className="px-4 py-3 font-normal">Price</th>
              <th className="px-4 py-3 font-normal">Per unit</th>
              <th className="px-4 py-3 font-normal">Availability</th>
              <th className="px-4 py-3 font-normal">Updated</th>
              <th className="px-4 py-3 font-normal" />
            </tr>
          </thead>
          <tbody>
            {data.prices.map((row) => {
              const isCheapest =
                data.cheapest?.retailer_id === row.retailer_id &&
                data.cheapest.price === row.price;
              return (
                <tr
                  key={`${row.retailer_id}-${row.url}`}
                  className={`border-b border-[var(--line)] last:border-b-0 ${
                    isCheapest ? "cheapest-row" : ""
                  }`}
                >
                  <td className="px-4 py-4 font-medium">
                    <a
                      href={row.url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-[var(--line)] underline-offset-2 hover:text-[var(--accent)]"
                    >
                      {row.retailer_name}
                    </a>
                    {isCheapest ? (
                      <span className="ml-2 text-xs text-[var(--accent)]">
                        Cheapest
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-4 text-sm text-[var(--ink-soft)]">
                    {row.product_name}
                  </td>
                  <td className="px-4 py-4">{formatPkr(row.price)}</td>
                  <td className="px-4 py-4 text-sm text-[var(--ink-soft)]">
                    {row.unit_price
                      ? `${formatPkr(row.unit_price.amount)}/${row.unit_price.unit.replace("Rs/", "")}`
                      : "—"}
                  </td>
                  <td className="px-4 py-4">
                    {row.availability === "in_stock" ? "In stock" : "Out of stock"}
                  </td>
                  <td className="px-4 py-4">
                    <FreshnessBadge freshness={row.freshness} />
                  </td>
                  <td className="px-4 py-4">
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
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-sm text-[var(--ink-soft)]">
        Prices are last checked at the time shown. Retailer sites can change.
      </p>
    </div>
  );
}
