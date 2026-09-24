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
  title: "PriceWise — Know the Price. Own the Choice",
  description:
    "Compare available prices across Pakistan and choose where you want to shop.",
  icons: {
    icon: [
      { url: "/icon.png", type: "image/png", sizes: "512x512" },
      { url: "/favicon.png", type: "image/png", sizes: "192x192" },
    ],
    apple: [{ url: "/icon.png", type: "image/png" }],
  },
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
