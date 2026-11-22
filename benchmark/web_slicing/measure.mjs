import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';
import { staticServer, launchOptions } from './serve.mjs';
import { configureNetwork, sampler, installPaintWatcher } from './instrument.mjs';

const [work,caseId,method,network,python,coldArg='5',repeatArg='5'] = process.argv.slice(2);
const here = fileURLToPath(new URL('.',import.meta.url));
const nCold=Number(coldArg);
const repeats=Number(repeatArg);
const trame=method==='S-local'||method==='S-remote';
const data=path.join(work,'data_'+caseId);
const config=JSON.parse(fs.readFileSync(path.join(data,'case.json'),'utf8'));
const out=path.join(work,'trial_'+[caseId,method,network].join('_'));
fs.mkdirSync(out,{recursive:true});
const record={case:caseId,method,network,requestedColdRuns:nCold,requestedSwitchRepeats:repeats,cold:[],switches:[]};
const summaryPath=path.join(out,'trial.json');
const save=()=>fs.writeFileSync(summaryPath,JSON.stringify(record,null,2)+'\n');
const pause=ms=>new Promise(r=>setTimeout(r,ms));
const startProcess=(args,stdout,env=process.env)=>{
  const fd=fs.openSync(stdout,'w');
  const p=spawn(args[0],args.slice(1),{windowsHide:true,stdio:['ignore',fd,fd],env});
  fs.closeSync(fd);
  return p;
};
const events=()=>fs.existsSync(serverLog)?fs.readFileSync(serverLog,'utf8').trim().split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line)):[];
const serverLog=path.join(out,'server_events.jsonl');
function wSectionBounds(root) {
  // Keep all prescribed depths in the stock viewer's startup clipping range.
  const indexRoute = '/model_cache/index.json';
  const boundsRoute = '/model_cache/r6_camera_bounds.vtp';
  const rawIndex = fs.readFileSync(path.join(root, indexRoute.slice(1)), 'utf8');
  const index = JSON.parse(rawIndex);
  const [xmin, xmax] = [config.positions[0] - 1, config.positions.at(-1) + 1];
  const [, , , , y, z, , , , radius] = config.camera;
  const points = [xmin,y-radius,z-radius,xmax,y+radius,z+radius,xmin,y+radius,z-radius].join(' ');
  const vtp = `<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
    <PolyData><Piece NumberOfPoints="3" NumberOfVerts="0" NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="1">
    <Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">${points}</DataArray></Points>
    <Polys><DataArray type="Int32" Name="connectivity" format="ascii">0 1 2</DataArray>
    <DataArray type="Int32" Name="offsets" format="ascii">3</DataArray></Polys>
    </Piece></PolyData></VTKFile>`;
  index.stages[0].layers.push({id:'r6_camera_bounds',label:'Benchmark camera bounds',role:'supplementary',
    kind:'exterior',file:boundsRoute.slice(1),bytes:Buffer.byteLength(vtp),points:3,cells:1});
  return {[indexRoute]:JSON.stringify(index,null,2)+'\n',[boundsRoute]:vtp};
}
let app;
let service;
let browser;
let processSampler;
try {
  if(trame){
    if(fs.existsSync(serverLog)) fs.renameSync(serverLog,serverLog+'.before-'+Date.now());
    const port=Number(process.env.SIM2WEB_R6_TRAME_PORT||18781);
    const url='http://127.0.0.1:'+port;
    const argv=[python,path.join(here,'trame_app.py'),method.slice(2),path.join(data,'case.json'),String(port),serverLog];
    const start=performance.now();
    service=startProcess(argv,path.join(out,'server_stdout.log'),{...process.env,SIM2WEB_R6_TRAME_LIB:path.join(work,'trame_lib')});
    record.server={argv,wrapperPid:service.pid};
    let listening=false;
    for(let i=0;i<220;i++){
      if(service.exitCode!==null)throw Error('trame server quit early: '+service.exitCode);
      try{if((await fetch(url,{signal:AbortSignal.timeout(1000)})).ok && events().length){listening=true;break;}}catch{}
      await pause(500);
    }
    if(!listening)throw Error('trame server startup timed out');
    record.server.startupWallMs=performance.now()-start;
    record.server.load=events()[0];
    app={url,close(){}};
  }else if(method==='B'){
    const check=JSON.parse(fs.readFileSync(path.join(work,'check_'+caseId,'correctness.json'),'utf8'));
    if(!check.passed)throw Error('Correctness gate failed: premium metrics withheld');
    app=await staticServer(path.join(work,'browser_dist'),{data});
  }else{
    const root=path.join(work,'site_'+caseId);
    app=await staticServer(root,{overlays:wSectionBounds(root)});
    const layers=[...config.layers.map(x=>x+':0:1'),'r6_camera_bounds:1:0'];
    const params=new URLSearchParams({field:'TotalDisplacement',axis:'x',pos:String(config.positions[config.first_index]),section:'1',
      parallel:'1',range:'full',layers:layers.join(','),cam:config.camera.join(',')});
    app.url += '/index.html?prefetch=0#'+params.toString();
  }
  for(let i=0;i<nCold;i++){
    const sample={run:i+1,pageErrors:[],consoleErrors:[]};
    let heapPeak=0, heapSamples=0, heapTimer, heapPending=false;
    let page;
    const pStart=performance.now();
    try {
      processSampler=await sampler(python,path.join(here,'sampler.py'),record.server?.load?.pid||service?.pid);
      browser=await chromium.launch(launchOptions);
      const context=await browser.newContext({viewport:{width:1600,height:900},deviceScaleFactor:1});
      page=await context.newPage();
      page.on('crash',()=>sample.crashed=true);
      page.on('pageerror',e=>sample.pageErrors.push(String(e)));
      page.on('console',m=>{if(m.type()==='error')sample.consoleErrors.push(m.text().slice(0,500));});
      await page.addInitScript(installPaintWatcher,{remoteView:method==='S-remote',firstIndex:config.first_index});
      const cdp=await context.newCDPSession(page);
      await cdp.send('Performance.enable');
      async function heap(){
        if(heapPending)return;
        heapPending=true;
        try{
          const r=await cdp.send('Performance.getMetrics');
          heapPeak=Math.max(heapPeak,r.metrics.find(x=>x.name==='JSHeapUsedSize')?.value||0);
          heapSamples++;
        }catch{}finally{heapPending=false;}
      }
      heapTimer=setInterval(heap,100);
      const stats=await configureNetwork(page,cdp,network,trame,false);
      await page.goto(app.url,{waitUntil:'commit',timeout:60000});
      if(method==='B')await page.waitForFunction(()=>window.__R6__?.firstImage,null,{timeout:150000,polling:80});
      else if(method==='W')await page.waitForFunction(()=>window.__SIM2WEB__?.summary()?.events?.firstRender,null,{timeout:150000,polling:80});
      else await page.waitForFunction(()=>window.__r6Paint?.complete,null,{timeout:150000,polling:80});
      const first = await page.evaluate(m=>{
        const webgl=document.createElement('canvas').getContext('webgl2');
        const ext=webgl?.getExtension('WEBGL_debug_renderer_info');
        const gpu=ext ? webgl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : (webgl?.getParameter(webgl.RENDERER)||null);
        if(m==='B')return {ms:window.__R6__.firstImage,timeOrigin:performance.timeOrigin,ready:window.__R6__.timings,gpu};
        if(m==='W'){
          const s=window.__SIM2WEB__.summary();
          return {ms:s.events.firstRender,timeOrigin:performance.timeOrigin,ready:s.startupFiles.filter(x=>x.role==='section'),events:s.events,gpu};
        }
        return {ms:window.__r6Paint.complete.ms,timeOrigin:performance.timeOrigin,paint:window.__r6Paint.complete,gpu};
      },method);
      sample.first=first;
      sample.transferAtFirst=stats.upTo(first.timeOrigin+first.ms);
      sample.browserVersion=browser.version();
      sample.firstMemory=await processSampler.snapshot();
      sample.firstJsHeap=heapPeak;
      if(i===nCold-1 && repeats>0){
        async function toggle(index){
          const t=performance.now();
          const previous={...stats};
          let details;
          if(method==='B'){
            details=await page.evaluate(async i=>{
              const t=performance.now();
              const r=await window.__R6__.select(i);
              return {...r,ms:performance.now()-t};
            },index);
          }else if(method==='W'){
            details=await page.evaluate(async i=>{
              const t=performance.now();
              const r=await window.__SIM2WEB__.setSection('x',i);
              return {...r,ms:performance.now()-t};
            },config.w_indices[index]);
          }else{
            const arm=await page.evaluate(i=>{
              const t=performance.now();
              const epoch=window.__r6Paint.arm(i);
              const old=Number(document.querySelector('#revision').textContent);
              const slider=document.querySelector('#section');
              slider.value=i;
              slider.dispatchEvent(new Event('input',{bubbles:true}));
              return {t,epoch,old};
            },index);
            const handle=await page.waitForFunction(({old,epoch})=>{
              const rev=Number(document.querySelector('#revision').textContent);
              const p=window.__r6Paint.complete;
              return rev>old && p?.epoch===epoch?p:false;
            },arm,{timeout:30000,polling:16});
            const paint=await handle.jsonValue();
            await handle.dispose();
            details={paint,ms:paint.ms-arm.t};
          }
          return {target:index,x:config.positions[index],timing:details,externalWallMs:performance.now()-t,
            wire:{httpBytes:stats.httpBytes-previous.httpBytes,wsIn:stats.incomingWsBytes-previous.incomingWsBytes,
              wsOut:stats.outgoingWsBytes-previous.outgoingWsBytes,delayed:stats.framesDelayed-previous.framesDelayed}};
        }
        record.warmup=[];
        // The initial section is index 4. Start at 0, then visit each once.
        for(let j=0;j<10;j++) record.warmup.push(await toggle(j));
        record.switchCpuStart=await processSampler.snapshot();
        for(let round=0;round<repeats;round++){
          for(let j=0;j<10;j++)record.switches.push({round:round+1,...await toggle(j)});
          save();
        }
        record.switchCpuEnd=await processSampler.snapshot();
        if(trame)record.server.allEvents=events();
        await page.screenshot({path:path.join(out,'section_1600x900.png'),timeout:20000}).catch(e=>sample.screenshotError=String(e));
        if(process.env.SIM2WEB_R6_CAMERA_QA==='1'){
          for(const j of config.correctness_indices.slice(0,-1)){
            await toggle(j);
            await page.screenshot({path:path.join(out,`section_${j}_1600x900.png`),timeout:20000});
          }
        }
      }
      sample.status='ok';
    }catch(e){sample.status=sample.crashed?'crash':'error';sample.error=String(e);console.error(sample.error);}
    finally {
      clearInterval(heapTimer);
      if(processSampler){
        sample.memory=await processSampler.snapshot().catch(()=>null);
        processSampler.close();processSampler=null;
      }
      sample.jsHeapPeak=heapPeak;
      sample.jsHeapSamples=heapSamples;
      sample.wallMs=performance.now()-pStart;
      record.cold.push(sample);
      save();
      console.log(JSON.stringify({run:sample.run,status:sample.status,firstMs:sample.first?.ms,
        transfer:sample.transferAtFirst,message:sample.error}));
      if(browser){await Promise.race([browser.close(),pause(4000)]);browser=null;}
    }
  }
}finally{
  app?.close();
  if(service){
    if(fs.existsSync(serverLog))record.server.allEvents=events();
    const kill=spawn('taskkill.exe',['/PID',String(service.pid),'/T','/F'],{windowsHide:true,stdio:'ignore'});
    record.server.stopExit=await new Promise(r=>kill.on('exit',r));
  }
  save();
}
if(record.cold.some(x=>x.status!=='ok')||record.switches.length!==10*repeats)process.exitCode=1;
