import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
const [repo, siteArg, out] = process.argv.slice(2);
const site=path.resolve(siteArg);
const { chromium }=createRequire(path.join(repo,"package.json"))("playwright-core");
const server=http.createServer((req,res)=>{
  const p=path.join(site,decodeURIComponent(new URL(req.url,"http://x").pathname));
  if(!p.startsWith(site)||!fs.existsSync(p)||fs.statSync(p).isDirectory()){res.writeHead(404).end();return;}
  res.writeHead(200,{"Content-Type":{".html":"text/html",".js":"text/javascript",".css":"text/css",".json":"application/json"}[path.extname(p)]||"application/octet-stream","Cache-Control":"no-store"});
  fs.createReadStream(p).pipe(res);
});
await new Promise(r=>server.listen(0,"127.0.0.1",r));
const browser=await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",headless:false,args:["--ignore-gpu-blocklist","--enable-unsafe-swiftshader"]});
try{
  const page=await browser.newPage({viewport:{width:1600,height:900}});
  await page.goto("http://127.0.0.1:"+server.address().port+"/index.html?prefetch=0");
  await page.waitForFunction(()=>window.__SIM2WEB__?.summary().events.firstRender,null,{timeout:60000});
  const samples=await page.evaluate(async()=>{
    const time=[];
    const fields=["Stress_Min_Principal","Stress_Mid_Principal","Stress_Max_Principal","TotalDisplacement"];
    for(const f of fields){
      const t=performance.now();
      await window.__SIM2WEB__.setField(f);
      await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
      const after=window.__SIM2WEB__.describeActors();
      time.push({field:f,ms:performance.now()-t,verified:Object.values(after).some(a=>a.array===f && a.arrayFound)});
    }
    return time;
  });
  const sorted=samples.map(r=>r.ms).sort((a,b)=>a-b);
  const result={samples,median_ms:(sorted[1]+sorted[2])/2,note:"4 field transitions; application API then two animation frames."};
  fs.writeFileSync(out,JSON.stringify(result,null,2)+"\n");
  console.log(result);
  if(!samples.every(r=>r.verified))process.exitCode=1;
}finally{await browser.close();server.close();}

