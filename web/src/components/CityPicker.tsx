"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { getCities, type CityOption } from "@/lib/api";

const STORAGE_KEY = "pricewise_city";

export const CITY_COORDS: Record<string, { lat: number; lng: number }> = {
  Karachi: { lat: 24.8607, lng: 67.0011 },
  Lahore: { lat: 31.5204, lng: 74.3587 },
  Islamabad: { lat: 33.6844, lng: 73.0479 },
  Rawalpindi: { lat: 33.5651, lng: 73.0169 },
  Faisalabad: { lat: 31.4504, lng: 73.135 },
  Multan: { lat: 30.1575, lng: 71.5249 },
};

function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function nearestCity(lat: number, lng: number): string {
  let best = "Karachi";
  let bestDist = Number.POSITIVE_INFINITY;
  for (const [name, coords] of Object.entries(CITY_COORDS)) {
    const d = haversineKm({ lat, lng }, coords);
    if (d < bestDist) {
      bestDist = d;
      best = name;
    }
  }
  return best;
}

export function readStoredCity(): string {
  if (typeof window === "undefined") return "all";
  return localStorage.getItem(STORAGE_KEY) || "all";
}

export function writeStoredCity(city: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, city);
}

/** Canonical city query value: "all" or display name like "Karachi". */
export function normalizeCityParam(raw: string | null | undefined): string {
  if (!raw || raw === "all" || raw === "all-pakistan") return "all";
  // Accept slug ids from older URLs (e.g. rawalpindi → Rawalpindi).
  const cleaned = raw.replace(/-/g, " ").trim();
  if (!cleaned) return "all";
  if (cleaned.toLowerCase() === "islamabad") return "Islamabad";
  return cleaned.replace(/\b\w/g, (c) => c.toUpperCase());
}

type Props = {
  /** Controlled value; when omitted, syncs from URL / localStorage. */
  value?: string;
  onChange?: (city: string) => void;
  /** When true, changing city updates the current URL search params. */
  syncUrl?: boolean;
  className?: string;
  /** Light text/controls for dark hero backgrounds. */
  variant?: "default" | "hero";
};

export function CityPicker({
  value,
  onChange,
  syncUrl = false,
  className = "",
  variant = "default",
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [cities, setCities] = useState<CityOption[]>([
    { id: "all", name: "All Pakistan", nationwide: true },
  ]);
  const [selected, setSelected] = useState(() =>
    normalizeCityParam(value || "all"),
  );
  const [locating, setLocating] = useState(false);
  const [locError, setLocError] = useState<string | null>(null);

  const isHero = variant === "hero";
  const labelClass = isHero ? "text-sm text-[var(--hero-muted)]" : "text-sm";
  const selectClass = isHero
    ? "ml-2 rounded-lg border border-[rgba(255,200,214,0.45)] bg-[rgba(255,255,255,0.12)] px-2 py-1 text-[var(--hero-fg)]"
    : "ml-2 rounded-lg border border-[var(--line)] bg-transparent px-2 py-1";
  const btnClass = isHero
    ? "rounded-lg border border-[rgba(255,200,214,0.45)] bg-[rgba(255,255,255,0.12)] px-2 py-1 text-sm text-[var(--blush)] hover:bg-[rgba(255,255,255,0.2)] disabled:opacity-60"
    : "rounded-lg border border-[var(--line)] px-2 py-1 text-sm text-[var(--accent)] hover:bg-[rgba(243,197,211,0.35)] disabled:opacity-60";

  useEffect(() => {
    getCities()
      .then((data) => {
        if (data.cities?.length) setCities(data.cities);
      })
      .catch(() => null);
  }, []);

  useEffect(() => {
    if (value !== undefined) {
      setSelected(normalizeCityParam(value));
      return;
    }
    const fromUrl = searchParams.get("city");
    if (fromUrl) {
      const next = normalizeCityParam(fromUrl);
      setSelected(next);
      writeStoredCity(next);
      return;
    }
    setSelected(normalizeCityParam(readStoredCity()));
  }, [value, searchParams]);

  function applyCity(city: string) {
    const next = normalizeCityParam(city);
    setSelected(next);
    writeStoredCity(next);
    onChange?.(next);
    if (syncUrl) {
      const params = new URLSearchParams(searchParams.toString());
      if (!next || next === "all") params.delete("city");
      else params.set("city", next);
      // Drop store when city changes — it may not serve the new city.
      params.delete("store");
      const qs = params.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname);
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setLocError("Location not supported in this browser.");
      return;
    }
    setLocating(true);
    setLocError(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const name = nearestCity(pos.coords.latitude, pos.coords.longitude);
        applyCity(name);
        setLocating(false);
      },
      () => {
        setLocError("Could not read location. Pick a city manually.");
        setLocating(false);
      },
      { enableHighAccuracy: false, timeout: 10000 },
    );
  }

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      <label className={labelClass}>
        City
        <select
          value={selected}
          onChange={(e) => applyCity(e.target.value)}
          className={selectClass}
          aria-label="Filter stores by city"
        >
          {cities.map((c) => (
            <option key={c.id} value={c.nationwide ? "all" : c.name}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={useMyLocation} disabled={locating} className={btnClass}>
        {locating ? "Locating…" : "Use my location"}
      </button>
      {locError ? (
        <span className={`text-xs ${isHero ? "text-[var(--blush)]" : "text-[var(--danger)]"}`}>
          {locError}
        </span>
      ) : null}
    </div>
  );
}
