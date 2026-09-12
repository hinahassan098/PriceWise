import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header site-shell flex items-center justify-between py-6">
      <Link
        href="/"
        className="brand-mark text-3xl text-[var(--accent-deep)] transition hover:text-[var(--accent)]"
      >
        PriceWise
      </Link>
      <nav className="flex items-center gap-5 text-sm text-[var(--ink-soft)]">
        <Link
          href="/search?q=surf%20excel"
          className="transition hover:text-[var(--accent)]"
        >
          Search
        </Link>
        <Link href="/admin" className="transition hover:text-[var(--accent)]">
          Admin
        </Link>
      </nav>
    </header>
  );
}
