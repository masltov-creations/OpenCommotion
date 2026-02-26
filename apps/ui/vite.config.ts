import { defineConfig } from 'vitest/config'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const uiPackageJson = JSON.parse(readFileSync(resolve(__dirname, 'package.json'), 'utf-8')) as { version?: string }
const uiVersion = uiPackageJson.version || '0.0.0'

export default defineConfig({
  define: {
    __OPENCOMMOTION_UI_VERSION__: JSON.stringify(uiVersion),
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
})
