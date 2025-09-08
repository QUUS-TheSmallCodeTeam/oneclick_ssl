import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API routes를 사용하므로 static export는 제거
  images: {
    unoptimized: true
  }
};

export default nextConfig;
