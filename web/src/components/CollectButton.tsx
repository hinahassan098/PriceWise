"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const STORAGE_KEY = "pricewise_admin_key";

export function CollectButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [adminKey, setAdminKey] = useState("");

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) setAdminKey(saved);
    } catch {
      // sessionStorage may be unavailable
    }
  }, []);

  async function runCollect() {
    const key = adminKey.trim();
    if (!key) {
      setMessage("Enter the admin API key to run collection.");
      return;
    }
    setBusy(true);
    setMessage("Collecting all live stores…");
    try {
      try {
        sessionStorage.setItem(STORAGE_KEY, key);
      } catch {
        // ignore
      }
      const res = await fetch("/api/admin/collect-all?max_products=80", {
        method: "POST",
        headers: {
          "X-Admin-Key": key,
        },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail
                  .map((d: { msg?: string }) => d.msg)
                  .filter(Boolean)
                  .join("; ")
              : "Collection failed";
        throw new Error(detail);
      }
      const summary = (data.jobs || [])
        .map(
          (j: { retailer_id: string; items_upserted: number; status: string }) =>
            `${j.retailer_id}:${j.items_upserted}`,
        )
        .join(", ");
      setMessage(summary ? `Done — ${summary}` : "Done");
      router.refresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Collection failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col items-stretch gap-2 sm:items-end">
      <label className="flex flex-col gap-1 text-sm text-[var(--ink-soft)]">
        Admin API key
        <input
          type="password"
          autoComplete="off"
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          placeholder="X-Admin-Key"
          className="min-w-[16rem] rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-[var(--ink)]"
        />
      </label>
      <button
        type="button"
        disabled={busy}
        onClick={runCollect}
        className="btn-accent rounded-xl px-4 py-2 disabled:opacity-60"
      >
        {busy ? "Collecting…" : "Collect all live stores"}
      </button>
      {message ? <p className="text-sm text-[var(--ink-soft)]">{message}</p> : null}
    </div>
  );
}
