import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Next's CLI subprocess can lose captured output on Node 24. The compiler
  // API performs the same build-time type check and is portable across lanes.
  experimental: { useTypeScriptCli: false },
};

export default nextConfig;
