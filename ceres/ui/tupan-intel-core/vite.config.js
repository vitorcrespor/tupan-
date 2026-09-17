import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { fileURLToPath } from 'node:url'

// The desktop client uses a same-origin proxy in local development. Production
// builds continue to use the absolute API URL supplied by their environment.
export default defineConfig(({ mode }) => {
  // Shared backend configuration lives in ceres/.env while the desktop
  // client keeps its own Vite env file. Load both, but explicitly bridge only
  // the browser-safe Maps key so backend credentials never enter the bundle.
  const sharedEnvDir = fileURLToPath(new URL('../../', import.meta.url))
  const sharedEnv = loadEnv(mode, sharedEnvDir, '')
  const clientEnv = loadEnv(mode, process.cwd(), '')
  const env = { ...sharedEnv, ...clientEnv }
  const apiProxyTarget = env.VITE_DEV_API_PROXY_TARGET?.replace(/\/+$/, '')
  const googleMapsApiKey = env.VITE_GOOGLE_MAPS_API_KEY || env.GOOGLE_MAPS_API_KEY || ''

  return {
    plugins: [react()],
    // Google Maps browser keys must be restricted by HTTP referrer in Google
    // Cloud. This explicit define does not expose any other shared env value.
    define: {
      'import.meta.env.VITE_GOOGLE_MAPS_API_KEY': JSON.stringify(googleMapsApiKey),
    },
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
