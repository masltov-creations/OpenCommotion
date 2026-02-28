import { defineConfig } from '@playwright/test'
import { readFileSync } from 'fs'
import { resolve } from 'path'

/** Read runtime port assignments written by dev_up.sh */
function readPortsEnv(): Record<string, string> {
  try {
    const lines = readFileSync(resolve(__dirname, 'runtime/agent-runs/ports.env'), 'utf-8').split('\n')
    const out: Record<string, string> = {}
    for (const line of lines) {
      const eq = line.indexOf('=')
      if (eq > 0) out[line.slice(0, eq).trim()] = line.slice(eq + 1).trim()
    }
    return out
  } catch {
    return {}
  }
}

const portsEnv    = readPortsEnv()
const uiDevPort   = process.env.PLAYWRIGHT_UI_PORT           ?? portsEnv.UI_DEV_PORT       ?? '5173'
const orchPort    = process.env.PLAYWRIGHT_ORCHESTRATOR_PORT ?? portsEnv.ORCHESTRATOR_PORT ?? '8001'
const gwPort      = process.env.PLAYWRIGHT_GATEWAY_PORT      ?? portsEnv.GATEWAY_PORT      ?? '8000'

// Expose to test files — set before any worker spawns
process.env.PLAYWRIGHT_ORCHESTRATOR_URL ??= `http://127.0.0.1:${orchPort}`
process.env.PLAYWRIGHT_GATEWAY_URL      ??= `http://127.0.0.1:${gwPort}`

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: `http://127.0.0.1:${uiDevPort}`,
    headless: true,
  },
  reporter: 'list',
})
