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
      <section className="hero-stage px-6 py-16 md:px-14 md:py-24">
        <div
          className="hero-orb"
          style={{
            width: 260,
            height: 260,
            top: "-60px",
            right: "4%",
            background: "rgba(243, 197, 211, 0.4)",
          }}
        />
        <div
          className="hero-orb"
          style={{
            width: 180,
            height: 180,
            bottom: "8%",
            left: "4%",
            background: "rgba(155, 45, 74, 0.5)",
            animationDelay: "1.4s",
          }}
        />
        <div
          className="hero-orb"
          style={{
            width: 120,
            height: 120,
            top: "42%",
            right: "28%",
            background: "rgba(255, 245, 248, 0.12)",
            animationDelay: "2.2s",
          }}
        />

        <div className="hero-content max-w-3xl">
          <Image
            src="/logo-mark.png"
            alt="PriceWise"
            width={96}
            height={96}
            priority
            className="hero-logo mb-6 h-16 w-16 rounded-full md:h-20 md:w-20"
          />
          <p className="brand-mark mb-4 text-6xl leading-none text-[var(--hero-fg)] md:text-8xl">
            PriceWise
          </p>
          <h1 className="max-w-xl text-2xl font-normal leading-snug text-[var(--hero-fg)] md:text-3xl">
            Know the Price. Own the Choice.
          </h1>
          <p className="mt-4 max-w-lg text-base leading-relaxed text-[var(--hero-muted)] md:text-lg">
            Compare available prices across Pakistan and choose where you want to
            shop.
          </p>
          <div className="mt-10 text-[var(--ink)]">
            <SearchBox
              autofocus
              size="hero"
              placeholder="What do you want to buy?"
              buttonLabel="Show Prices"
            />
          </div>
          <p className="mt-5 text-sm text-[var(--hero-muted)]">
            See the difference before you buy.
          </p>
        </div>
      </section>

      <section
        className="mt-16 md:mt-20"
        style={{ animation: "rise-in 0.7s ease-out 0.12s both" }}
      >
        <p className="section-kicker">Browse</p>
        <h2 className="brand-mark mt-2 text-3xl text-[var(--accent-deep)] md:text-4xl">
          Popular categories
        </h2>
        <p className="mt-2 max-w-xl text-[var(--ink-soft)]">
          Packaged grocery first. Fresh produce and loose items come later.
        </p>
        <div className="mt-6 border-t border-[var(--line)]">
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
