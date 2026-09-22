import { SearchBox } from "@/components/SearchBox";
import { SearchResultsClient } from "@/components/SearchResultsClient";

type Props = {
  searchParams: Promise<{
    q?: string;
    store?: string;
    stock?: string;
    city?: string;
  }>;
};

export default async function SearchPage({ searchParams }: Props) {
  const params = await searchParams;
  const q = (params.q || "").trim();
  const store = params.store || undefined;
  const stock = params.stock || undefined;
  const city = params.city || undefined;

  return (
    <div className="site-shell">
      <div className="mb-8">
        <SearchBox initialQuery={q} size="compact" showCity={false} />
      </div>

      {!q ? (
        <p className="text-[var(--ink-soft)]">Enter a product to compare prices.</p>
      ) : (
        <SearchResultsClient q={q} store={store} stock={stock} city={city} />
      )}
    </div>
  );
}
