/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: false, // Disable for WebSocket connections
};

module.exports = nextConfig;
