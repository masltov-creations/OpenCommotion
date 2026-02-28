/**
 * Visual scene screenshot capture script.
 * Usage: npx ts-node --esm scripts/capture_visual_scenes.ts
 *   or:  npx playwright test --project=chromium scripts/capture_visual_scenes.ts (not recommended)
 *
 * Driven by Playwright; runs against the live dev server at http://127.0.0.1:8000.
 * For each prompt it:
 *  1. Loads the UI
 *  2. Submits the prompt
 *  3. Waits for "Patch count:" to appear (visual has rendered)
 *  4. Takes a full screenshot into docs/assets/
 */

import { chromium, type Page } from '@playwright/test'
import * as path from 'path'
import * as fs from 'fs'

const BASE_URL = 'http://127.0.0.1:8000'
const OUT_DIR = path.resolve(__dirname, '..', 'docs', 'assets', 'scenes')

const PROMPTS: { label: string; prompt: string }[] = [
  { label: 'rocket-motion', prompt: 'draw a rocket with motion' },
  { label: 'house', prompt: 'draw a house' },
  { label: 'sunset', prompt: 'draw a sunset' },
  { label: 'planet', prompt: 'draw a planet' },
  { label: 'butterfly-3d', prompt: 'draw a 3D butterfly' },
  { label: 'cloud', prompt: 'draw a cloud' },
  { label: 'moon', prompt: 'show the moon' },
  { label: 'car', prompt: 'draw a red car' },
]

async function runPrompt(page: Page, prompt: string): Promise<void> {
  // Clear any existing prompt text
  const promptInput = page.getByPlaceholder('Say something or type a prompt…').or(
    page.getByPlaceholder('Prompt')
  )
  await promptInput.fill(prompt)
  await page.getByRole('button', { name: /Run Turn/i }).click()
  // Wait for patch count to appear (visual rendered)
  await page.waitForSelector('text=Patch count:', { timeout: 20_000 })
  await page.waitForTimeout(600) // let the animation settle
}

async function main(): Promise<void> {
  fs.mkdirSync(OUT_DIR, { recursive: true })

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } })
  const page = await context.newPage()

  // Base screenshot: initial UI
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await page.waitForSelector('[data-testid="visual-stage-card"]', { timeout: 15_000 })
  await page.screenshot({ path: path.join(OUT_DIR, 'ui-baseline.png'), fullPage: false })
  console.log('✓ ui-baseline.png')

  for (const { label, prompt } of PROMPTS) {
    try {
      // Fresh page load so state is clean
      await page.goto(BASE_URL, { waitUntil: 'networkidle' })
      await page.waitForSelector('[data-testid="visual-stage-card"]', { timeout: 15_000 })
      await runPrompt(page, prompt)
      const outFile = path.join(OUT_DIR, `${label}.png`)
      await page.screenshot({ path: outFile, fullPage: false })
      console.log(`✓ ${label}.png  («${prompt}»)`)
    } catch (err) {
      console.error(`✗ ${label}: ${String(err)}`)
    }
  }

  await browser.close()
  console.log(`\nScreenshots saved to ${OUT_DIR}`)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
