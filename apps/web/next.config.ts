import type { NextConfig } from "next";

// Allow `next/image` to optimize remote previews coming from Backblaze B2.
// Presigned download URLs use the bucket-specific S3 hostname pattern:
//   <bucket>.s3.<region>.backblazeb2.com    (path-style and virtual-host)
//   s3.<region>.backblazeb2.com             (path-style)
// One wildcard covers every region + bucket, so this config drops in
// without per-deployment tweaks.
const nextConfig: NextConfig = {
  transpilePackages: ["@clay-geospatial-embeddings/shared"],
  // Dev-only: Next 16's cross-origin guard 403s `_next/static/*` unless the dev
  // origin is allow-listed. The app's own Playwright config serves it at
  // `127.0.0.1` (to dodge macOS localhost→::1), so list both the IP and the
  // hostname or React never hydrates and every click is silently dead.
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**.backblazeb2.com",
      },
    ],
  },
};

export default nextConfig;
