import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {openBrowser,measureText,paint,writeJson} from '../figures_r7/capture_common.mjs';
import {staticServer} from '../web_slicing/serve.mjs';

const [site, settingsFile, destination] = process.argv.slice(2);
const settings = JSON.parse(await fs.readFile(settingsFile,'utf8'));
await fs.mkdir(destination,{recursive:true});
const modelCss = `.panel.collapsed, .right { display: none !important; }`;
const legendCss = `.panel, .viewport { visibility: hidden !important; }
.shell { background: #fff !important; }
.right { inset: 0 !important; align-items: stretch !important; }
.legend { border: 0 !important; box-shadow: none !important; border-radius: 0 !important;
  background: #fff !important; padding: 8px 8px 12px !important; }
.legend-title { font: 700 25px/1.2 Arial, sans-serif !important; margin-bottom: 9px !important; }
.legend-sub { display: none !important; }
.legend .bands { flex-direction: row !important; margin: 0 60px !important;
  font: 400 24px/1 Arial, sans-serif !important; }
.legend .band-row { position: relative; display: block !important; flex: 1 1 0;
  height: 62px !important; }
.legend .band-row .swatch.tall { width: 100%; height: 24px !important; border: 0; }
.legend .band-row.last { flex: 0 0 0; }
.legend .tick { position: absolute; left: 0; top: 30px; transform: translateX(-50%) !important;
  white-space: nowrap; }
`;
const browser = await openBrowser();
const server = await staticServer(site,{gzip:false});
const metadata={...settings,modelCss,legendCss,panels:{}};
async function open(page,stage) {
  const hash = new URLSearchParams({stage,field:settings.field,range:'custom',rmin:settings.limits[0],rmax:settings.limits[1],
    parallel:'1',cam:settings.camera.join(','),section:'0',cmap:'jet',bands:'8',layers:'excavation:1:1'});
  await page.goto(`${server.url}/index.html?prefetch=0&figure_stage=${encodeURIComponent(stage)}#${hash}`);
  await page.waitForFunction(()=>window.__SIM2WEB__?.summary()?.events.firstRender,null,{timeout:240000});
  const state=await page.evaluate(()=>({active:window.__SIM2WEB__.activeColoring(),actors:Object.keys(window.__SIM2WEB__.describeActors())}));
  assert.deepEqual([state.active.min,state.active.max],settings.limits);
  assert.equal(state.active.name,settings.field);
  assert.deepEqual(state.actors,['layer:excavation']);
  assert.equal((await page.locator('.panel section:has(h2:text-is("Stage")) select option:checked').innerText()).split('. ').at(-1),stage);
}
try {
  const panel=await browser.newPage({viewport:settings.viewport,deviceScaleFactor:3});
  for(const stage of settings.stages){
    await open(panel,stage);
    await panel.locator('.panel .collapse').click();
    await panel.addStyleTag({content:modelCss});
    await paint(panel);
    const file=`stage_${stage}.png`;
    await panel.screenshot({path:path.join(destination,file),scale:'device'});
    metadata.panels[stage]={file,dsf:3};
  }
  await panel.close();
  const legend=await browser.newPage({viewport:{width:1180,height:260},deviceScaleFactor:4});
  await open(legend,settings.stages[0]);
  await legend.addStyleTag({content:legendCss});
  await paint(legend);
  const groups={legend_title:'.legend-title',legend_tick:'.tick'};
  const text=await measureText(legend,groups);
  assert.equal(text.filter(t=>t.role==='legend_tick').length,9);
  metadata.legend={file:'legend.png',dsf:4,text};
  await legend.locator('.legend').screenshot({path:path.join(destination,'legend.png'),scale:'device'});
  await writeJson(path.join(destination,'capture.json'),metadata);
  console.log('Captured',settings.stages.join(', '),'and a shared legend');
} finally { await browser.close(); server.close(); }
