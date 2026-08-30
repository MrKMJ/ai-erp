/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Type errors still fail the build; ESLint is optional here (no eslint-config-next
  // dependency bundled). Add `eslint-config-next` + an .eslintrc and remove this to lint.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
