import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone tracing creates symlinks that require Windows Developer Mode.
  // Enable it only inside the Linux Docker builder.
  ...(process.env.NEXT_OUTPUT_STANDALONE === "true" ? { output: "standalone" as const } : {}),
  transpilePackages: ["@una/api-client", "@una/shared-types"],
};

export default nextConfig;
