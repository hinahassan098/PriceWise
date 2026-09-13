import Image from "next/image";
import Link from "next/link";
import { SearchBox } from "@/components/SearchBox";

const CATEGORIES = [
  { label: "Grocery", href: "/search?q=atta" },
  { label: "Beverages", href: "/search?q=coke" },
  { label: "Personal Care", href: "/search?q=lifebuoy" },
  { label: "Household", href: "/search?q=surf%20excel" },
  { label: "Snacks", href: "/search?q=sooper" },
  { label: "Baby Care", href: "/search?q=pampers" },
];

export default function HomePage() {
  return (
    <div className="site-shell">
      <section className="hero-stage px-6 py-16 md:px-12 md:py-24">
        <div
          className="hero-orb"
          style={{
            width: 220,
            height: 220,
            top: "-40px",
            right: "8%",
            background: "rgba(243, 197, 211, 0.35)",
          }}
        />
        <div
          className="hero-orb"
          style={{
            width: 160,
            height: 160,
            bottom: "12%",
            left: "6%",
            background: "rgba(155, 45, 74, 0.45)",
            animationDelay: "1.4s",
          }}
        />
        <div className="hero-content max-w-3xl">
          <Image
            src="/logo-mark.png"
            alt="PriceWise"
            width={96}
            height={96}
            priority
            className="mb-5 h-16 w-16 rounded-full md:h-20 md:w-20"
          />
          <p className="brand-mark mb-3 text-5xl text-[var(--hero-fg)] md:text-7xl">
            PriceWise
          </p>
          <h1 className="max-w-xl text-2xl font-normal leading-snug text-[var(--hero-fg)] md:text-3xl">
            Compare prices across Pakistan
          </h1>
          <p className="mt-3 max-w-lg text-base text-[var(--hero-muted)] md:text-lg">
            Search a product, see verified timestamps from retailers, and open
            the cheapest store to buy.
          </p>
          <div className="mt-8 text-[var(--ink)]">
            <SearchBox autofocus size="hero" />
          </div>
          <p className="mt-4 text-sm text-[var(--hero-muted)]">
            Try{" "}
            <Link href="/search?q=brite%201kg" className="underline decoration-[var(--blush)] underline-offset-4">
              Brite 1kg
            </Link>
            ,{" "}
            <Link href="/search?q=lays" className="underline decoration-[var(--blush)] underline-offset-4">
              Lays
            </Link>{" "}
            or{" "}
            <Link
              href="/search?q=Surf%20Excel%201kg"
              className="underline decoration-[var(--blush)] underline-offset-4"
            >
              Surf Excel 1kg
            </Link>
          </p>
        </div>
      </section>

      <section className="mt-14" style={{ animation: "rise-in 0.7s ease-out 0.12s both" }}>
        <h2 className="brand-mark text-3xl text-[var(--accent-deep)]">
          Popular categories
        </h2>
        <p className="mt-2 text-[var(--ink-soft)]">
          Packaged grocery first. Fresh produce and loose items come later.
        </p>
        <div className="mt-4 border-t border-[var(--line)]">
          {CATEGORIES.map((category) => (
            <Link key={category.label} href={category.href} className="category-link text-lg">
              {category.label}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
