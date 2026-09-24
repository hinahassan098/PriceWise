"use client";

import {
  FormEvent,
  KeyboardEvent,
  Suspense,
  useEffect,
  useRef,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { suggestProducts, type Suggestion } from "@/lib/api";
import { CityPicker, normalizeCityParam, readStoredCity } from "@/components/CityPicker";

type Props = {
  initialQuery?: string;
  autofocus?: boolean;
  size?: "hero" | "compact";
  showCity?: boolean;
  placeholder?: string;
  buttonLabel?: string;
};

function SearchBoxInner({
  initialQuery = "",
  autofocus = false,
  size = "hero",
  showCity = true,
  placeholder = 'Search products… e.g. "Lays" or "Surf Excel"',
  buttonLabel = "Compare",
}: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [suggesting, setSuggesting] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  // After picking a suggestion, ignore the next suggest response so the menu stays closed.
  const suppressSuggestRef = useRef(false);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      abortRef.current?.abort();
      setSuggestions([]);
      setOpen(false);
      setActive(-1);
      setSuggesting(false);
      return;
    }

    if (suppressSuggestRef.current) {
      return;
    }

    const handle = window.setTimeout(() => {
      if (suppressSuggestRef.current) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setSuggesting(true);
      suggestProducts(q, controller.signal)
        .then((data) => {
          if (controller.signal.aborted || suppressSuggestRef.current) return;
          const next = data.suggestions || [];
          setSuggestions(next);
          setOpen(next.length > 0);
          setActive(-1);
        })
        .catch((err) => {
          if (controller.signal.aborted || err?.name === "AbortError") return;
        })
        .finally(() => {
          if (!controller.signal.aborted) setSuggesting(false);
        });
    }, 120);

    return () => {
      window.clearTimeout(handle);
    };
  }, [query]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  useEffect(() => {
    function onPointerDown(event: MouseEvent | TouchEvent) {
      const root = rootRef.current;
      if (!root || !open) return;
      const target = event.target as Node | null;
      if (target && !root.contains(target)) {
        closeSuggestions();
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("touchstart", onPointerDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("touchstart", onPointerDown);
    };
  }, [open]);

  function closeSuggestions() {
    abortRef.current?.abort();
    setOpen(false);
    setActive(-1);
    setSuggesting(false);
  }

  function cityParam() {
    return normalizeCityParam(searchParams.get("city") || readStoredCity());
  }

  function buildSearchUrl(q: string) {
    const params = new URLSearchParams();
    params.set("q", q);
    const store = searchParams.get("store");
    const stock = searchParams.get("stock");
    const city = cityParam();
    if (store) params.set("store", store);
    if (stock) params.set("stock", stock);
    if (city && city !== "all") params.set("city", city);
    return `/search?${params.toString()}`;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (!q) return;
    suppressSuggestRef.current = true;
    setSuggestions([]);
    closeSuggestions();
    router.push(buildSearchUrl(q));
  }

  /** Suggestions only complete the input — they never navigate or search. */
  function selectSuggestion(item: Suggestion) {
    suppressSuggestRef.current = true;
    abortRef.current?.abort();
    setQuery(item.query || item.label);
    setSuggestions([]);
    closeSuggestions();
  }

  function onQueryChange(value: string) {
    suppressSuggestRef.current = false;
    setQuery(value);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      closeSuggestions();
      return;
    }
    if (!open || suggestions.length === 0) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => (i + 1) % suggestions.length);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    }
  }

  const showMenu = open && suggestions.length > 0;

  return (
    <div className={`w-full ${size === "hero" ? "max-w-2xl" : "max-w-xl"}`}>
      {showCity ? (
        <div className="mb-3">
          <CityPicker syncUrl={size === "compact"} variant={size === "hero" ? "hero" : "default"} />
        </div>
      ) : null}
      <div ref={rootRef} className="relative z-30">
        <form
          onSubmit={onSubmit}
          className="panel search-field relative z-10 flex overflow-hidden rounded-2xl"
        >
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onFocus={() => {
              if (!suppressSuggestRef.current && suggestions.length > 0) setOpen(true);
            }}
            onBlur={() => {
              window.setTimeout(() => {
                if (!rootRef.current?.contains(document.activeElement)) {
                  closeSuggestions();
                }
              }, 120);
            }}
            onKeyDown={onKeyDown}
            autoFocus={autofocus}
            autoComplete="off"
            role="combobox"
            aria-expanded={showMenu}
            aria-controls="search-suggestions"
            aria-autocomplete="list"
            placeholder={placeholder}
            className={`w-full bg-transparent px-5 outline-none placeholder:text-[var(--ink-soft)] ${
              size === "hero" ? "py-4 text-lg" : "py-3 text-base"
            }`}
            aria-label="Search products"
          />
          <button type="submit" className="btn-accent px-6 font-medium tracking-wide">
            {suggesting ? "…" : buttonLabel}
          </button>
        </form>
        {showMenu ? (
          <ul
            id="search-suggestions"
            role="listbox"
            className="absolute left-0 right-0 top-full z-50 mt-1 max-h-72 overflow-y-auto rounded-2xl border border-[var(--line)] bg-[#fffafb] text-[var(--ink)]"
            style={{
              backgroundColor: "#fffafb",
              boxShadow: "0 16px 36px rgba(42, 16, 24, 0.16)",
            }}
          >
            {suggestions.map((item, idx) => {
              const selected = idx === active;
              const rowClass = `flex w-full flex-col gap-0.5 border-b border-[var(--line)] px-4 py-3 text-left last:border-b-0 transition-colors ${
                selected
                  ? "bg-[rgba(243,197,211,0.55)]"
                  : "bg-[#fffafb] hover:bg-[rgba(243,197,211,0.35)]"
              }`;
              return (
                <li
                  key={`${item.source}-${item.variant_id ?? item.label}-${idx}`}
                  role="option"
                  aria-selected={selected}
                >
                  <button
                    type="button"
                    className={rowClass}
                    onMouseDown={(e) => e.preventDefault()}
                    onMouseEnter={() => setActive(idx)}
                    onClick={() => selectSuggestion(item)}
                  >
                    <SuggestionRow item={item} query={query} />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : null}
      </div>
    </div>
  );
}

function SuggestionRow({ item, query }: { item: Suggestion; query: string }) {
  return (
    <>
      <span className="block text-[15px] font-medium leading-snug text-[var(--ink)]">
        {highlightMatch(item.label, query)}
      </span>
      <span className="text-sm text-[var(--ink-soft)]">
        {[item.size_label, item.brand, item.source === "live" ? "live" : null]
          .filter(Boolean)
          .join(" · ")}
      </span>
    </>
  );
}

function highlightMatch(label: string, query: string) {
  const q = query.trim();
  if (!q) return label;
  const idx = label.toLowerCase().indexOf(q.toLowerCase());
  if (idx < 0) return label;
  return (
    <>
      {label.slice(0, idx)}
      <mark className="bg-transparent font-semibold text-[var(--accent-deep)]">
        {label.slice(idx, idx + q.length)}
      </mark>
      {label.slice(idx + q.length)}
    </>
  );
}

export function SearchBox(props: Props) {
  return (
    <Suspense
      fallback={
        <div
          className={`w-full ${props.size === "hero" ? "max-w-2xl" : "max-w-xl"} h-14 panel rounded-2xl`}
        />
      }
    >
      <SearchBoxInner {...props} />
    </Suspense>
  );
}
