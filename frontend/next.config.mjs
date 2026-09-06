/** @type {import('next').NextConfig} */

// Build target:
//   NEXT_OUTPUT=export     -> fully static site in ./out (Cloudflare Pages, Netlify,
//                             Render static, GitHub Pages, Vercel — all free, no card)
//   default ("standalone") -> small Node server bundle for the Docker image (Fly.io)
// Every page here is a client component with no server data fetching, so the static
// export is complete and identical in behaviour.
const output = process.env.NEXT_OUTPUT === "export" ? "export" : "standalone";

const nextConfig = {
  reactStrictMode: true,
  output,
  images: { unoptimized: true },
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
