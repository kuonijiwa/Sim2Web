// Walk through the six workbench steps with real clicks and take screenshots.
//   node benchmark/workbench_walkthrough.mjs --url http://127.0.0.1:8765/workbench/ \
//        --model path/to/model.vtu --out shots/ [--order XX,YY,ZZ,XY,YZ,XZ] [--unit Pa] [--spacing 20]
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const a = Object.fromEntries(process.argv.slice(2).reduce((acc, v, i, arr) => (v.startsWith('--') ? [...acc, [v.slice(2), arr[i + 1]]] : acc), []));
mkdirSync(a.out, { recursive: true });
const browser = await chromium.launch({ executablePath: a.browser || process.env.CHROME_PATH || '/usr/bin/google-chrome',
  args: ['--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--use-angle=swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
const shot = async (name) => { await page.waitForTimeout(400); await page.screenshot({ path: join(a.out, `${name}.png`) }); console.log('shot', name); };
const idle = async (timeout = 900000) => {
  await page.waitForTimeout(300);
  await page.waitForFunction(() => !document.querySelector('.log-toggle')?.textContent.includes('running'), null, { timeout });
};
const step = async (label) => { await page.click(`.step:has-text("${label}")`); await page.waitForTimeout(200); };

await page.goto(a.url);
await page.waitForSelector('.steps');
await shot('01_empty');

await page.click('text=Add model files…');
const dir = a.model.replace(/[\\/][^\\/]+$/, '');
const file = a.model.split(/[\\/]/).pop();
await page.fill('.dialog .path input', dir);
await page.click('.dialog button:has-text("Go")');
await page.click(`.entries li:has-text("${file}")`);
await shot('02_file_dialog');
await page.click('.dialog button:has-text("Add")');
await page.click('button:has-text("Read model")');
await idle();
await shot('03_model_read');

await step('Fields and units');
await shot('04_fields_drafted');
if (a.order) await page.selectOption('.row:has-text("Component order") select', a.order);
if (a.unit) await page.locator('.row').filter({ has: page.locator('label', { hasText: /^Unit$/ }) }).nth(1).locator('select').selectOption(a.unit);
await page.waitForTimeout(800);
await shot('05_fields_set');

await step('Geometry and excavation');
await page.click('.form button:text-is("Preview surfaces")');
await idle();
await page.waitForTimeout(6000);
await shot('06_preview');

await step('Sections');
if (a.spacing) { await page.fill('.row:has-text("Spacing") input', a.spacing); await page.press('.row:has-text("Spacing") input', 'Tab'); }
await page.waitForTimeout(800);
await shot('07_sections');

await step('Build and validate');
await page.click('.form button:text-is("Build package")');
await idle();
await page.click('.form button:text-is("Validate")');
await idle();
await page.waitForTimeout(6000);
await shot('08_built_validated');

await step('Publish and export');
await shot('09_publish');
await page.click('.modes button:has-text("View")');
await page.waitForTimeout(3000);
await shot('10_view_mode');
await browser.close();
