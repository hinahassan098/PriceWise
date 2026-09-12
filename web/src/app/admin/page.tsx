import Link from "next/link";
import { CollectButton } from "@/components/CollectButton";
import { getAdminJobs, getAdminStats, getRetailers } from "@/lib/api";

export default async function AdminPage() {
  const [stats, retailers, jobs] = await Promise.all([
    getAdminStats().catch(() => null),
    getRetailers().catch(() => ({ retailers: [] })),
    getAdminJobs().catch(() => ({ jobs: [] })),
  ]);

  return (
    <div className="site-shell">
      <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="brand-mark text-4xl text-[var(--accent-deep)]">Admin</h1>
          <p className="mt-2 text-[var(--ink-soft)]">
            Retailer sync status, collection jobs, and catalog counts.
          </p>
        </div>
        <CollectButton />
      </div>

      {!stats ? (
        <p className="text-[var(--danger)]">
          API unreachable. Start the backend on port 8020.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          {[
            ["Products", stats.products],
            ["Variants", stats.variants],
            ["Retailer SKUs", stats.retailer_products],
            ["Prices", stats.prices],
            ["Reviews", stats.matching_reviews],
            ["Job errors", stats.jobs_error],
            ["Checked rows", stats.updated_today],
          ].map(([label, value]) => (
            <div key={String(label)} className="panel rounded-2xl p-4">
              <p className="text-sm text-[var(--ink-soft)]">{label}</p>
              <p className="mt-1 text-3xl">{value}</p>
            </div>
          ))}
        </div>
      )}

      <h2 className="brand-mark mt-10 text-3xl text-[var(--accent-deep)]">Retailers</h2>
      <div className="panel mt-4 overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left">
          <thead className="border-b border-[var(--line)] text-sm text-[var(--ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-normal">Store</th>
              <th className="px-4 py-3 font-normal">Status</th>
              <th className="px-4 py-3 font-normal">Platform</th>
              <th className="px-4 py-3 font-normal">Last sync</th>
            </tr>
          </thead>
          <tbody>
            {retailers.retailers.map((row) => (
              <tr key={row.id} className="border-b border-[var(--line)] last:border-b-0">
                <td className="px-4 py-3">
                  <a href={row.website_url} target="_blank" rel="noreferrer" className="underline">
                    {row.name}
                  </a>
                </td>
                <td className="px-4 py-3 capitalize">{row.status}</td>
                <td className="px-4 py-3">{row.platform || "—"}</td>
                <td className="px-4 py-3 text-sm text-[var(--ink-soft)]">
                  {row.last_successful_sync
                    ? new Date(row.last_successful_sync).toLocaleString()
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="brand-mark mt-10 text-3xl text-[var(--accent-deep)]">Recent jobs</h2>
      <div className="panel mt-4 overflow-x-auto rounded-2xl">
        <table className="min-w-full text-left">
          <thead className="border-b border-[var(--line)] text-sm text-[var(--ink-soft)]">
            <tr>
              <th className="px-4 py-3 font-normal">ID</th>
              <th className="px-4 py-3 font-normal">Retailer</th>
              <th className="px-4 py-3 font-normal">Status</th>
              <th className="px-4 py-3 font-normal">Items</th>
              <th className="px-4 py-3 font-normal">Error</th>
            </tr>
          </thead>
          <tbody>
            {jobs.jobs.length === 0 ? (
              <tr>
                <td className="px-4 py-4 text-[var(--ink-soft)]" colSpan={5}>
                  No jobs yet. Run Collect all live stores.
                </td>
              </tr>
            ) : (
              jobs.jobs.map((job) => (
                <tr key={job.id} className="border-b border-[var(--line)] last:border-b-0">
                  <td className="px-4 py-3">{job.id}</td>
                  <td className="px-4 py-3">{job.retailer_id}</td>
                  <td className="px-4 py-3">{job.status}</td>
                  <td className="px-4 py-3">{job.items_upserted}</td>
                  <td className="px-4 py-3 text-sm text-[var(--danger)]">
                    {job.error || "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-6 text-sm text-[var(--ink-soft)]">
        <Link href="/" className="underline">
          Back to search
        </Link>
      </p>
    </div>
  );
}
