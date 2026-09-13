"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function CollectButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runCollect() {
    setBusy(true);
    setMessage("Collecting all live stores…");
    try {
      // Same-origin proxy keeps ADMIN_API_KEY on the server.
      const res = await fetch("/api/admin/collect-all?max_products=80", {
        method: "POST",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join("; ")
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
    <div className="flex flex-col items-start gap-2">
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
