"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { suggestProducts } from "@/lib/api";

type Props = {
  initialQuery?: string;
  autofocus?: boolean;
  size?: "hero" | "compact";
};

function SearchBoxInner({
  initialQuery = "",
  autofocus = false,
  size = "hero",
}: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<
    { variant_id: number; label: string; size_label: string }[]
  >([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    if (query.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    const handle = window.setTimeout(async () => {
      try {
        const data = await suggestProducts(query.trim());
        setSuggestions(data.suggestions);
        setOpen(true);
      } catch {
        setSuggestions([]);
      }
    }, 220);
    return () => window.clearTimeout(handle);
  }, [query]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    setOpen(false);
    const params = new URLSearchParams();
    params.set("q", q);
    const store = searchParams.get("store");
    const stock = searchParams.get("stock");
    if (store) params.set("store", store);
    if (stock) params.set("stock", stock);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <div className={`relative w-full ${size === "hero" ? "max-w-2xl" : "max-w-xl"}`}>
      <form onSubmit={onSubmit} className="panel flex overflow-hidden rounded-2xl">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 150)}
          autoFocus={autofocus}
          placeholder='Search products… e.g. "Surf Excel 1kg"'
          className={`w-full bg-transparent px-5 outline-none placeholder:text-[var(--ink-soft)] ${
            size === "hero" ? "py-4 text-lg" : "py-3 text-base"
          }`}
          aria-label="Search products"
        />
        <button type="submit" className="btn-accent px-5 font-medium">
          Compare
        </button>
      </form>
      {open && suggestions.length > 0 ? (
        <ul className="panel absolute z-20 mt-2 w-full overflow-hidden rounded-xl shadow-none">
          {suggestions.map((item) => (
            <li key={item.variant_id}>
              <Link
                href={`/product/${item.variant_id}`}
                className="block border-b border-[var(--line)] px-4 py-3 last:border-b-0 hover:bg-[rgba(243,197,211,0.35)]"
                onMouseDown={(e) => e.preventDefault()}
              >
                <span className="block font-medium">{item.label}</span>
                <span className="text-sm text-[var(--ink-soft)]">{item.size_label}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function SearchBox(props: Props) {
  return (
    <Suspense fallback={<div className={`w-full ${props.size === "hero" ? "max-w-2xl" : "max-w-xl"} h-14 panel rounded-2xl`} />}>
      <SearchBoxInner {...props} />
    </Suspense>
  );
}
