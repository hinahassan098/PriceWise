import { NextResponse } from "next/server";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production"
    ? "https://pricewise-api-dauj.onrender.com"
    : "http://127.0.0.1:8000");

export async function POST(request: Request) {
  const adminKey = process.env.ADMIN_API_KEY?.trim();
  if (!adminKey) {
    return NextResponse.json(
      { detail: "ADMIN_API_KEY is not configured on the web service" },
      { status: 503 },
    );
  }

  const { searchParams } = new URL(request.url);
  const maxProducts = searchParams.get("max_products") || "80";
  const upstream = `${API_BASE}/api/admin/collect/all?max_products=${encodeURIComponent(maxProducts)}`;

  try {
    const res = await fetch(upstream, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "X-Admin-Key": adminKey,
      },
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
    const text = await res.text();
    let data: unknown = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: text || "Upstream returned non-JSON" };
    }
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      {
        detail:
          err instanceof Error ? err.message : "Failed to reach PriceWise API",
      },
      { status: 502 },
    );
  }
}
