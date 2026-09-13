/**
 * Headless smoke for the mobile app API layer (no device required).
 * Run: node scripts/mobile-smoke.mjs
 */
const API_BASE = process.env.API_BASE || "https://pricewise-api-dauj.onrender.com";

async function main() {
  const results = [];
  const check = (id, ok, notes) => {
    results.push({ id, status: ok ? "PASS" : "FAIL", notes });
    console.log(`${ok ? "PASS" : "FAIL"} ${id} — ${notes}`);
  };

  try {
    const health = await fetch(`${API_BASE}/api/health`, { signal: AbortSignal.timeout(120000) });
    const hj = await health.json();
    check("MB-wake", health.ok && hj.ok === true, `health ${health.status}`);
  } catch (e) {
    check("MB-wake", false, String(e));
  }

  try {
    const res = await fetch(`${API_BASE}/api/search?q=lays&live=true`, {
      signal: AbortSignal.timeout(45000),
    });
    const data = await res.json();
    const n = (data.results || []).length;
    const flat = (data.all_store_prices || []).length;
    check("MB-01", res.ok && n >= 1, `results=${n} flat=${flat} mode=${data.mode}`);
    const httpsOk = (data.all_store_prices || []).slice(0, 10).every((o) => String(o.url || "").startsWith("https://"));
    check("MB-04-urls", httpsOk, "offer urls are https");
  } catch (e) {
    check("MB-01", false, String(e));
  }

  // Empty query should be rejected by API (app UI also blocks empty submit).
  try {
    const res = await fetch(`${API_BASE}/api/search`, { signal: AbortSignal.timeout(20000) });
    check("MB-03", res.status === 422, `empty search status=${res.status}`);
  } catch (e) {
    check("MB-03", false, String(e));
  }

  const failed = results.filter((r) => r.status === "FAIL").length;
  console.log(`\nSummary: ${results.length - failed}/${results.length} passed`);
  process.exit(failed ? 1 : 0);
}

main();
