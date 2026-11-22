import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { staticServer, launchOptions } from './serve.mjs';

const [dist,data,out] = process.argv.slice(2);
fs.mkdirSync(out,{recursive:true});
const caseInfo=JSON.parse(fs.readFileSync(path.join(data,'case.json'),'utf8'));
const server=await staticServer(dist,{data,output:out});
const browser=await chromium.launch(launchOptions);
try {
  const page=await browser.newPage({viewport:{width:1600,height:900}});
  page.on('pageerror',e=>console.error(String(e)));
  page.on('crash',()=>console.error('Chromium tab crashed'));
  await page.goto(server.url);
  await page.waitForFunction(()=>window.__R6__?.firstImage,null,{timeout:120000});
  for (const index of caseInfo.correctness_indices) {
    const m = await page.evaluate(async i => {
      const api=window.__R6__;
      const stats=await api.select(i);
      const {points,values,polys}=api.geometry;
      const header= new Uint32Array([values.length,polys.length/4]);
      const r=await fetch('/result/'+i,{method:'POST',body:new Blob([header,points,values,polys])});
      if(!r.ok)throw Error(r.statusText);
      return stats;
    }, index);
    console.log(JSON.stringify(m));
  }
  await page.screenshot({path:path.join(out,'browser_correctness.png')});
} finally { await browser.close(); server.close(); }
