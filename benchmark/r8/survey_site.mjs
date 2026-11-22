import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright-core';

const [url, destination] = process.argv.slice(2);
await fs.mkdir(destination, {recursive:true});
const browser = await chromium.launch({executablePath:process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  args:['--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
try {
  const page = await browser.newPage({viewport:{width:1600,height:900}});
  const origin = new URL(url).origin;
  // Listen to the publication's ordinary page load. Do not fetch any additional products.
  let publication;
  page.on('response', response => {
    const address = new URL(response.url());
    if (!publication && address.origin === origin && /\/index\.json$/.test(address.pathname) && response.ok()) {
      publication = response.body().then(body => ({url:response.url(),body}));
    }
  });
  const navigation = await page.goto(url, {waitUntil:'domcontentloaded',timeout:90000});
  if (!navigation?.ok()) throw Error(`Publication returned HTTP ${navigation?.status()}`);
  await page.waitForFunction(() => document.querySelector('canvas') && document.querySelector('select option')
    && !document.body.innerText.includes('正在载入'),
    null, {timeout:75000});
  if (!publication) throw Error('The initial viewer load did not request an index.json');
  const {url:indexUrl, body} = await publication;
  const index = JSON.parse(body.toString('utf8'));
  await fs.writeFile(path.join(destination,'index.json'),body);
  const stageList = await page.evaluate(() => {
    const api=window.__SIM2WEB__ || window.__SIMWEBVIEW__;
    return {title:document.querySelector('h1,h2,h3')?.textContent.trim(), ids:api?.stages?.() || null,
      menus:[...document.querySelectorAll('select')].map(s=>[...s.options].map(o=>o.textContent.trim()))};
  });
  await page.screenshot({path:path.join(destination,'chrome.png'),timeout:20000});
  const legacy = !index.schema && !Array.isArray(index.stages);
  const stages = legacy ? Object.entries(index).map(([id,s])=>({id,label:id,
    cavity:s.cavity, fields:s.fields, sectionCounts:Object.fromEntries(Object.entries(s.slices || {}).map(([a,x])=>[a,x.length]))}))
    : (index.stages || []).map(stage=>({
      id:stage.id,label:stage.label,source:stage.source,
      layers:(stage.layers || []).map(x=>({id:x.id,kind:x.kind,bytes:x.bytes})),
      sectionCounts:Object.fromEntries(Object.entries(stage.sections || {}).map(([axis,list])=>[axis,list.length])),
    }));
  const summary = {page:page.url(),index:indexUrl,chrome:browser.version(),schema:index.schema ?? 'legacy stage-keyed index without schema field',
    title:index.title ?? index.viewer?.title ?? null,solver:index.solver ?? null,ui:stageList,
    fields:legacy ? [...new Set(stages.flatMap(s=>s.fields || []))] : Object.keys(index.fields || {}),stages};
  await fs.writeFile(path.join(destination,'stage_list.json'),JSON.stringify(summary,null,2)+'\n');
  console.log(JSON.stringify({schema:summary.schema,model:summary.title,stages:summary.stages.map(s=>s.label || s.name || s.id),chrome:summary.chrome}));
} finally {
  await browser.close();
}
