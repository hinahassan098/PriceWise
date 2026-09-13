import Image from "next/image";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="site-header site-shell flex items-center justify-between py-5">
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
          className="h-10 w-10 rounded-full"
        />
        <span className="brand-mark text-2xl text-[var(--accent-deep)] md:text-3xl">
          PriceWise
        </span>
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
