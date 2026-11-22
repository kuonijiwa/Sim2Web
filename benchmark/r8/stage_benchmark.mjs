import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { configureNetwork } from '../web_slicing/instrument.mjs';
import { launchOptions, staticServer } from '../web_slicing/serve.mjs';

const [site, network, output, n='3'] = process.argv.slice(2);
assert(['LAN','4G'].includes(network));
const index = JSON.parse(await fs.readFile(path.join(site,'model_cache/index.json'),'utf8'));
const start = {axis:'x',value:38};
const axisSelector = '.panel section:has(.tabs) p.hint';
async function section(page) {
  const displayed = await page.locator(axisSelector).innerText();
  const values = displayed.match(/^([XYZ])\s*=\s*([-+.\d]+)\s+m/);
  assert(values,displayed);
  return {axis:values[1].toLowerCase(),value:Number(values[2])};
}
const axes = new URLSearchParams({axis:start.axis,pos:start.value,section:'1'});
const server = await staticServer(site);
const result = {network,window:[1600,900],profile:network==='4G'?{downloadMbit:20,uploadMbit:5,latencyMs:50}:null,stageIds:index.stages.map(s=>s.id),runs:[]};
try {
  for(let run=0;run<Number(n);run++) {
    const browser = await chromium.launch(launchOptions);
    try {
      const context = await browser.newContext({viewport:{width:1600,height:900},deviceScaleFactor:1});
      const page = await context.newPage();
      const errors=[];
      page.on('pageerror',e=>errors.push(String(e)));
      const cdp = await context.newCDPSession(page);
      const stats = await configureNetwork(page,cdp,network,false,false);
      await page.goto(`${server.url}/index.html?prefetch=0#${axes}`,{waitUntil:'commit',timeout:90000});
      await page.waitForFunction(()=>window.__SIM2WEB__?.summary()?.events.firstRender,null,{timeout:240000});
      const first = await page.evaluate(()=>({ms:window.__SIM2WEB__.summary().events.firstRender,origin:performance.timeOrigin}));
      const row={run:run+1,chrome:browser.version(),firstFrameMs:first.ms,firstFrameBytes:stats.upTo(first.origin+first.ms).httpBytes,switches:[],errors};
      assert.deepEqual(await section(page),start);
      const route = [...index.stages.keys()].slice(1);
      route.push(...[...index.stages.keys()].slice(0,-1).reverse());
      let prior=0;
      for (const stage of route) {
        const before=await section(page);
        const bytes=stats.httpBytes;
        const timing=await page.evaluate(async stage=>{
          const t=performance.now();
          await window.__SIM2WEB__.setStage(stage);
          return performance.now()-t;
        },stage);
        const after=await section(page);
        const current = await page.locator('.panel section').filter({has:page.getByRole('heading',{name:'Stage',exact:true})}).locator('select').inputValue();
        assert.equal(Number(current),stage);
        row.switches.push({direction:stage>prior?'forward':'backward',from:index.stages[prior].id,to:index.stages[stage].id,
          latencyMs:timing,encodedHttpBytes:stats.httpBytes-bytes,before,after,axisKept:before.axis===after.axis,positionKept:before.value===after.value});
        prior=stage;
      }
      assert.deepEqual(errors,[]);
      result.runs.push(row);
      await fs.writeFile(output,JSON.stringify(result,null,2)+'\n');
      console.log(`${network} ${run+1}: ${first.ms.toFixed(1)} ms to first frame, ${row.switches.length} switches`);
    } finally { await browser.close(); }
  }
} finally { server.close(); }
