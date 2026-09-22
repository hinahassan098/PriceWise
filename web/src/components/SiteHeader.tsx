import Image from "next/image";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="site-shell flex items-center justify-between py-4 md:py-5">
        <Link
          href="/"
          className="inline-flex items-center gap-2.5 transition opacity-95 hover:opacity-100"
          aria-label="PriceWise home"
        >
          <Image
            src="/logo-mark.png"
            alt=""
            width={40}
            height={40}
            priority
            className="h-9 w-9 rounded-full md:h-10 md:w-10"
          />
          <span className="brand-mark text-2xl text-[var(--accent-deep)] md:text-3xl">
            PriceWise
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm text-[var(--ink-soft)] md:gap-2">
          <Link
            href="/search?q=surf%20excel"
            className="rounded-xl px-3 py-1.5 transition hover:bg-[rgba(243,197,211,0.35)] hover:text-[var(--accent)]"
          >
            Search
          </Link>
          <Link
            href="/admin"
            className="rounded-xl px-3 py-1.5 transition hover:bg-[rgba(243,197,211,0.35)] hover:text-[var(--accent)]"
          >
            Admin
          </Link>
        </nav>
      </div>
    </header>
  );
}
