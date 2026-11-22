import { createRequire } from "node:module";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
const [repo, html, out, png, runCount, vtkjs] = process.argv.slice(2);
const require = createRequire(path.join(repo,"package.json"));
const { chromium } = require("playwright-core");
const contents = fs.statSync(html).size;
const srv = http.createServer((req,res) => {
  const url=new URL(req.url,"http://127.0.0.1");
  if (url.pathname==="/scene.vtkjs" && vtkjs) {
    res.writeHead(200,{"Content-Type":"application/octet-stream","Content-Length":fs.statSync(vtkjs).size,"Cache-Control":"no-store"});
    fs.createReadStream(vtkjs).pipe(res);
    return;
  }
  if (url.pathname!=="/scene.html") { res.writeHead(404).end(); return; }
  res.writeHead(200,{"Content-Type":"text/html","Cache-Control":"no-store","Content-Length":contents});
  fs.createReadStream(html).pipe(res);
});
await new Promise(r=>srv.listen(0,"127.0.0.1",r));
const output={exportBytes:vtkjs ? fs.statSync(vtkjs).size : contents, viewerBytes:vtkjs?contents:undefined, mode:vtkjs?'separate-vtkjs':'embedded-html', runs:[], method:"Fresh headful Chromium; on localhost with HTTP cache disabled; first WebGL triangles draw on a visible canvas with at least 10,000 indices on the large main canvas (excluding the 3,186-index orientation widget), followed by two requestAnimationFrame callbacks."};
try {
  for(let i=0;i<Number(runCount||3);i++){
    const browser=await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",headless:false,args:["--enable-precise-memory-info","--ignore-gpu-blocklist","--enable-unsafe-swiftshader","--disable-background-timer-throttling","--disable-backgrounding-occluded-windows"]});
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
            if(!window.__glanceFirst && args[0]===4 && count>=10000 && this.drawingBufferWidth>=600 && this.canvas?.getBoundingClientRect?.().width>600){
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
      const base="http://127.0.0.1:"+srv.address().port;
      page.on("response",r=>{if(r.url().endsWith(".vtkjs"))console.log("Scene HTTP",r.status());});
      console.log("Starting navigation",i+1);
      await page.goto(base+"/scene.html"+(vtkjs?"?name=scene.vtkjs&url="+encodeURIComponent(base+"/scene.vtkjs"):""),{waitUntil:"commit",timeout:45000});
      console.log("Navigation committed",i+1);
      try {
        await page.waitForFunction(()=>window.__glanceFirst?.firstImageMs,null,{timeout:140000});
        Object.assign(result,await page.evaluate(()=>window.__glanceFirst));
      } catch(e){result.failure=String(e);}
      console.log("Geometry timing",JSON.stringify({firstImageMs:result.firstImageMs,failure:result.failure,errorCount:result.errors.length}));
      output.runs[i]=result;
      fs.writeFileSync(out,JSON.stringify(output,null,2)+"\n");

    } catch(e){result.failure=String(e);}
    finally { await Promise.race([browser.close(),new Promise(r=>setTimeout(r,4000))]); }
    output.runs[i]=result;
    console.log(JSON.stringify(result));
    fs.writeFileSync(out, JSON.stringify(output,null,2)+"\n");
  }
} finally { srv.close(); }
process.exit(output.runs.some(r=>!r.firstImageMs)?1:0);

