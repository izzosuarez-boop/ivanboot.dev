import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-hosted in Docker: ship only the traced files + a minimal server.js
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  // Portfolio sections renamed/merged 2026-11-23: old links keep working. Temporary (307) on purpose, so a
  // browser doesn't cache them for good if the sections change again.
  async redirects() {
    return [
      { source: "/scraping", destination: "/automation", permanent: false },
      { source: "/software", destination: "/web-api", permanent: false },
      { source: "/ai-media", destination: "/ai-media-shopify", permanent: false },
      { source: "/web-shopify", destination: "/ai-media-shopify", permanent: false },
    ];
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "cdn.shopify.com" }],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
