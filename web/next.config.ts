import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === "development"
        ? "http://127.0.0.1:8000"
        : "https://pricewise-api-dauj.onrender.com"),
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.shopify.com",
      },
      {
        protocol: "https",
        hostname: "**.shopify.com",
      },
      {
        protocol: "https",
        hostname: "alfatah.pk",
      },
      {
        protocol: "https",
        hostname: "**.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "imtiaz-i.s3.ap-southeast-1.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "cdn.mafrservices.com",
      },
      {
        protocol: "https",
        hostname: "**.mafrservices.com",
      },
      {
        protocol: "https",
        hostname: "shop.imtiaz.com.pk",
      },
      {
        protocol: "https",
        hostname: "em-cdn.eatmubarak.pk",
      },
    ],
  },
};

export default nextConfig;
