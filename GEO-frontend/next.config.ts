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
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
};
module.exports = {
  allowedDevOrigins: ['local-origin.dev', '*.local-origin.dev'],
}
export default nextConfig;
