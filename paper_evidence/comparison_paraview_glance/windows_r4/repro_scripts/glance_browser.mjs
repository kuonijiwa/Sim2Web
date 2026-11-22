import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
const [repo, html, out, png, runCount] = process.argv.slice(2);
const require = createRequire(path.join(repo,"package.json"));
const { chromium } = require("playwright-core");
const contents = fs.statSync(html).size;
const srv = http.createServer((req,res) => {
  if (req.url!=="/scene.html") { res.writeHead(404).end(); return; }
  res.writeHead(200,{"Content-Type":"text/html","Cache-Control":"no-store","Content-Length":contents});
  fs.createReadStream(html).pipe(res);
});
await new Promise(r=>srv.listen(0,"127.0.0.1",r));
const output={exportBytes:contents, runs:[], method:"Fresh headful Chromium; on localhost with HTTP cache disabled; first WebGL triangles draw on a visible canvas with at least 24 indices (excluding fullscreen quad), followed by two requestAnimationFrame callbacks."};
try {
  for(let i=0;i<Number(runCount||3);i++){
    const browser=await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",headless:false,args:["--enable-precise-memory-info","--ignore-gpu-blocklist","--enable-unsafe-swiftshader"]});
    const result={run:i+1,browser:browser.version(),errors:[],failedRequests:[]};
    try {
      const context=await browser.newContext({viewport:{width:1600,height:900},deviceScaleFactor:1});
      const page=await context.newPage();
      const cdp=await context.newCDPSession(page);
      await cdp.send("Network.enable");
      await cdp.send("Network.setCacheDisabled",{cacheDisabled:true});
      page.on("pageerror",e=>result.errors.push(String(e)));
      page.on("requestfailed",r=>result.failedRequests.push([r.url(),r.failure()?.errorText]));
      await page.addInitScript(()=>{
        function monitor(ctx,name,kind){
          const f=ctx?.[name];
          if(!f || f.__r4) return;
          const fn=function(...args){
            const r=f.apply(this,args);
            const count=args[kind];
            if(!window.__glanceFirst && args[0]===4 && count>=24 && this.canvas?.getBoundingClientRect?.().width>50){
              const ext=this.getExtension("WEBGL_debug_renderer_info");
              window.__glanceFirst={count, drawMethod:name, firstDrawMs:performance.now(),renderer:ext ? this.getParameter(ext.UNMASKED_RENDERER_WEBGL) : this.getParameter(this.RENDERER)};
              requestAnimationFrame(()=>requestAnimationFrame(()=>window.__glanceFirst.firstImageMs=performance.now()));
            }
            return r;
          };
          fn.__r4=true;
          Object.defineProperty(ctx,name,{value:fn,writable:true,configurable:true});
        }
        for (const context of [window.WebGLRenderingContext,window.WebGL2RenderingContext]) {
          if(!context)continue;
          monitor(context.prototype,"drawElements",1); monitor(context.prototype,"drawArrays",2);
          monitor(context.prototype,"drawElementsInstanced",1); monitor(context.prototype,"drawArraysInstanced",2);
        }
      });
      await page.goto("http://127.0.0.1:"+srv.address().port+"/scene.html",{waitUntil:"commit",timeout:180000});
      try {
        await page.waitForFunction(()=>window.__glanceFirst?.firstImageMs,null,{timeout:180000});
        Object.assign(result,await page.evaluate(()=>window.__glanceFirst));
      } catch(e){result.failure=String(e);}
      if(i===0){
        await page.screenshot({path:png,timeout:60000});
        result.interfaceText=(await page.locator("body").innerText({timeout:15000})).slice(0,3000);
      }
    } catch(e){result.failure=String(e);}
    finally { await browser.close(); }
    output.runs.push(result);
    console.log(JSON.stringify(result));
    fs.writeFileSync(out, JSON.stringify(output,null,2)+"\n");
  }
} finally { srv.close(); }
if(output.runs.some(r=>!r.firstImageMs)) process.exitCode=1;
