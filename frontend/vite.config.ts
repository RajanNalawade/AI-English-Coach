import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // The deployed app sits behind a login; the manifest request must send it too.
      useCredentials: true,
      includeAssets: ['icon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'AI English Coach',
        short_name: 'English Coach',
        description: 'Practise English: grammar fixes, rephrasing and conversation.',
        theme_color: '#2563eb',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
      workbox: {
        // Never cache API answers; the coach needs the live model.
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: {
    // Lets phones on the same Wi-Fi open the dev server.
    host: true,
    // Vite rejects unknown host names; allow the HTTPS name Tailscale gives this PC (docs/PHONE.md).
    allowedHosts: ['.ts.net'],
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  preview: {
    host: true,
    port: 4173,
    allowedHosts: ['.ts.net'],
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
