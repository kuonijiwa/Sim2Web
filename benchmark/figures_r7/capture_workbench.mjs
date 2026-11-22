import assert from 'node:assert/strict';
import path from 'node:path';
import { measureText, openBrowser, paint, writeJson } from './capture_common.mjs';

// The interaction order follows benchmark/workbench_walkthrough.mjs.
const [url, model, output] = process.argv.slice(2);
const deviceScaleFactor = 4;
const common = `.top, .steps, .log, .nav-buttons { display: none !important; }
.app { grid-template-rows: auto; height: auto; background: #fff; }
.form, .diagnostics { overflow: visible; }
.form { padding: 16px 20px 14px; }
.form h2, .diagnostics h2 { font-size: 26px; line-height: 1.15; }
.form h3 { font-size: 22px; margin: 7px 0 5px; }
.form .notice, .diagnostics .title, .diagnostics .detail { font-size: 21px; line-height: 1.23; }
.form .notice { margin: 5px 0 0; }
`;
const fieldsCss = common + `.app { grid-template-columns: minmax(0, 2.14fr) minmax(0, 1fr); grid-template-areas: 'centre diag'; }
.centre { display: block; }
.viewer { display: none; }
.form .row { grid-template-columns: 155px minmax(0, 1fr); gap: 10px; padding: 4px 0; }
.form .row > label, .form .row select { font-size: 21px; }
.form .row select { max-width: 100%; font: 400 23px/1.2 'Arial Narrow', Arial, sans-serif; }
.form .row:nth-of-type(1), .form .row:nth-of-type(2), .form .row:nth-of-type(3), .form .row:nth-of-type(6),
.form h3:first-of-type, .form h3:last-of-type, .form > div > .hint, .form table.data, .form > div > p.muted,
.diagnostics li:not(.error):not(.ok) { display: none; }
.diagnostics { padding: 16px 14px; }
.diagnostics li { padding: 9px 10px; }
`;
const buildCss = common + `.app { grid-template-columns: minmax(0, 1fr); grid-template-areas: 'centre'; }
.centre { grid-template-rows: auto 268px; }
.diagnostics, .form > div > p.muted, .form > div > .inline { display: none; }
.form .hint, .form table.data { font-size: 20px; line-height: 1.12; }
.form table.data td, .form table.data th { padding: 3px 8px; }
.form table.data:nth-of-type(2) tbody tr:nth-child(n+4) { display: none; }
.viewer-label { font-size: 21px; }
`;
const embeddedCss = `.panel.collapsed { display: none !important; }
.right { display: none !important; }
`;

const browser = await openBrowser();
try {
  const page = await browser.newPage({ viewport: { width: 1120, height: 960 }, deviceScaleFactor });
  page.on('pageerror', error => console.error(error.message));
  const step = name => page.locator('.steps button').filter({ hasText: name }).click();
  const idle = () => page.waitForFunction(() => !document.querySelector('.log-toggle')?.textContent.includes('running'), null, { timeout: 600000 });
  const records = {};
  async function capture(key, css, groups) {
    const style = await page.addStyleTag({ content: css });
    await paint(page);
    const bounds = await page.locator('.app').boundingBox();
    assert(bounds.height <= 940, bounds.height);
    const clip = { x: 0, y: 0, width: 1120, height: Math.ceil(bounds.height) };
    const text = await measureText(page, groups);
    assert(text.length, key);
    await page.screenshot({ path: path.join(output, `fig2_${key}.png`), clip, scale: 'device' });
    records[key] = { clip, deviceScaleFactor, text, injectedCss: css };
    await style.evaluate(node => node.remove());
  }

  await page.goto(url);
  await page.locator('.steps').waitFor();
  await page.getByText('Add model files…', { exact: true }).click();
  await page.waitForFunction(() => document.querySelector('.dialog .path input')?.value);
  await page.locator('.dialog .path input').fill(path.dirname(model));
  await page.locator('.dialog').getByRole('button', { name: 'Go', exact: true }).click();
  await page.locator('.entries li').filter({ hasText: path.basename(model) }).click();
  await page.locator('.dialog').getByRole('button', { name: 'Add', exact: true }).click();
  await page.getByRole('button', { name: /^Read model/ }).click();
  await page.locator('.diagnostics .error').filter({ hasText: /component/i }).waitFor({ timeout: 120000 });
  await idle();

  await step('Fields and units');
  const order = page.locator('.row').filter({ has: page.getByText('Component order', { exact: true }) }).locator('select');
  assert.equal(await order.inputValue(), 'from_file');
  await page.locator('.diagnostics .ok').filter({ hasText: '16.5 kN/m³' }).waitFor();
  await capture('a', fieldsCss, {
    step: '.form h2', selector: '.form .row:nth-of-type(4)>label, .form .row:nth-of-type(4) select',
    file_warning: '.form .row:nth-of-type(4) .notice', blocked_build: '.diagnostics .error .detail',
    unit_weight: '.diagnostics .ok .detail',
  });
  await order.selectOption('XX,YY,ZZ,XY,YZ,XZ');
  const unit = page.locator('.row').filter({ has: page.locator('label', { hasText: /^Unit$/ }) }).nth(1).locator('select');
  await unit.selectOption('Pa');
  await page.locator('.diagnostics .error').waitFor({ state: 'hidden' });
  await step('Geometry and excavation');
  await page.getByRole('button', { name: 'Preview surfaces', exact: true }).click();
  await page.locator('.viewer-label').filter({ hasText: 'Preview: surfaces only' }).waitFor({ timeout: 180000 });
  await idle();
  await step('Sections');
  const spacing = page.locator('.row').filter({ hasText: 'Spacing' }).locator('input');
  await spacing.fill('20');
  await spacing.press('Tab');
  await step('Build and validate');
  await page.getByRole('button', { name: 'Build package', exact: true }).click();
  await page.locator('.viewer-label').filter({ hasText: 'Built package' }).waitFor({ timeout: 300000 });
  await idle();
  await page.getByRole('button', { name: 'Validate', exact: true }).click();
  await page.locator('.form .notice.ok').filter({ hasText: 'Passed: every checked value matches the source model.' }).waitFor({ timeout: 300000 });
  await idle();
  const iframe = await page.locator('iframe[title="Package viewer"]').elementHandle();
  const viewer = await iframe.contentFrame();
  await viewer.waitForFunction(() => window.__SIM2WEB__?.summary()?.events.firstRender, null, { timeout: 180000 });
  await viewer.locator('.collapse').click();
  await viewer.addStyleTag({ content: embeddedCss });
  await capture('b', buildCss, {
    step: '.form h2', build_result: '.form > div > .hint, .form h3, .form .data th, .form .data td',
    validation_pass: '.form .notice.ok', package_viewer: '.viewer-label',
  });
  records.b.embeddedCss = embeddedCss;
  await writeJson(path.join(output, 'workbench_capture.json'), records);
  for (const [panel, info] of Object.entries(records)) {
    console.log(`Figure 2 ${panel}: ${JSON.stringify(info.clip)}, smallest measured CSS ink height ${Math.min(...info.text.map(x => x.inkHeightCssPx))}`);
  }
} finally {
  await browser.close();
}
