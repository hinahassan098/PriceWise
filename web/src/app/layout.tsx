import { Cormorant_Garamond, Figtree } from "next/font/google";
import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/components/SiteHeader";

const display = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});

const body = Figtree({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "PriceWise — Compare grocery prices in Pakistan",
  description:
    "Search a product, compare verified prices across Pakistani retailers, and buy from the cheapest store.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} antialiased`}>
        <SiteHeader />
        <main className="pb-16">{children}</main>
      </body>
    </html>
  );
}
