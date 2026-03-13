import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  webpack: (config) => {
    const path = require('path');
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname, './src'),
      '@shared': path.resolve(__dirname, './shared'),
    };
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.FASTAPI_BASE_URL || 'http://backend:8000'}/:path*`,
      },
    ]
  },
};

export default nextConfig;
