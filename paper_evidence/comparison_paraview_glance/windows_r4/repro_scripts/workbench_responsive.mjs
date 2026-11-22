import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { createWriteStream, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
const [repo, sim, project, out, port] = process.argv.slice(2);
const { chromium }=createRequire(path.join(repo,"package.json"))("playwright-core");
mkdirSync(out,{recursive:true});
const command=[sim,"gui",project,"--port",port,"--no-browser"];
const service=spawn(command[0],command.slice(1),{windowsHide:true});
const log=createWriteStream(path.join(out,"service.log"));
service.stdout.pipe(log,{end:false});
service.stderr.pipe(log,{end:false});
const base="http://127.0.0.1:"+port;
const result={command,samples:[],errors:[]};
let browser;
try {
  for(let i=0;i<90;i++){
    try{if((await fetch(base+"/api/project")).ok)break;}catch{}
    if(i===89)throw Error("Workbench unavailable");
    await new Promise(r=>setTimeout(r,500));
  }
  browser=await chromium.launch({executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe",args:["--enable-unsafe-swiftshader","--ignore-gpu-blocklist"]});
  const page=await browser.newPage({viewport:{width:1600,height:900}});
  page.on("pageerror",e=>result.errors.push(e.message));
  await page.goto(base+"/workbench/");
  await page.locator(".step").filter({hasText:"Build and validate"}).click();
  const requested=page.waitForResponse(r=>r.url().endsWith("/api/jobs") && r.request().method()==="POST" && r.request().postDataJSON()?.kind === "build");
  await page.locator('.form button:text-is("Build package")').click();
  const response=await requested;
  result.buildRequestStatus=response.status();
  const {id}=await response.json();
  await page.waitForFunction(()=>document.querySelector(".log-toggle")?.textContent.includes("running"),null,{timeout:20000});
  for(const panel of ["Fields and units","Geometry and excavation","Sections","Build and validate"]){
    const t=performance.now();
    const previous=(await (await fetch(base+"/api/jobs/"+id)).json()).state;
    await page.locator(".step").filter({hasText:panel}).click({timeout:8000});
    const state=(await (await fetch(base+"/api/jobs/"+id)).json());
    const toggle=await page.locator(".log-toggle").innerText();
    result.samples.push({panel,jobBefore:previous,jobAfter:state.state,seconds:(performance.now()-t)/1000,toggle,job:state});
    if (panel==="Sections") await page.screenshot({path:path.join(out,"navigation_during_build.png"),timeout:20000});
    await page.waitForTimeout(4000);
  }
  const t=Date.now();
  let job;
  do {
    job=await (await fetch(base+"/api/jobs/"+id)).json();
    if (job.state!=="running")break;
    await page.waitForTimeout(1200);
  } while(Date.now()-t<600000);
  result.finalJob=job;
  result.logText=await page.locator(".log-toggle").innerText();
  result.usableDuringBuild=result.samples.filter(s=>s.jobBefore==="running" && s.jobAfter==="running").length;
  if(job.state!=="done") process.exitCode=1;
} catch(e){result.error=String(e);process.exitCode=1;}
finally{
  if(browser)await browser.close();
  const kill=spawn("taskkill",["/PID",String(service.pid),"/T","/F"],{windowsHide:true});
  result.stopExit=await new Promise(r=>kill.on("close",r));
  log.end();
  writeFileSync(path.join(out,"responsiveness.json"),JSON.stringify(result,null,2)+"\n");
  console.log(JSON.stringify({samples:result.samples.map(({panel,jobBefore,jobAfter,seconds,toggle})=>({panel,jobBefore,jobAfter,seconds,toggle})),usableDuringBuild:result.usableDuringBuild,error:result.error,finalState:result.finalJob?.state},null,2));
}

