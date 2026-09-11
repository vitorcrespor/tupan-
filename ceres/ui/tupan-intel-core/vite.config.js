import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { fileURLToPath } from 'node:url'

// The desktop client uses a same-origin proxy in local development. Production
// builds continue to use the absolute API URL supplied by their environment.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_DEV_API_PROXY_TARGET?.replace(/\/+$/, '')

  return {
    plugins: [react()],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: apiProxyTarget
        ? {
            '/api': {
              target: apiProxyTarget,
              changeOrigin: true,
            },
          }
        : undefined,
    },
    preview: {
      host: '127.0.0.1',
      port: 4173,
      strictPort: true,
    },
  }
})