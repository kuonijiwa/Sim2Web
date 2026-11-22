import fs from 'node:fs';
import {chromium} from 'playwright-core';
import {configureNetwork} from './instrument.mjs';
import {launchOptions} from './serve.mjs';

const [url,out]=process.argv.slice(2);
const results=[];
for(const [name,mode,shape] of [['LAN','LAN',false],['4G CDP only','4G',false],['4G CDP plus WS shaper','4G',true]]){
  const b=await chromium.launch(launchOptions);
  try{
    const p=await b.newPage();
    const s=await p.context().newCDPSession(p);
    const stats=await configureNetwork(p,s,mode,true,shape);
    await p.goto(url);
    const roundtripMs=await p.evaluate(async()=>{
      const ws=new WebSocket('ws://'+location.host+'/echo');
      ws.binaryType='arraybuffer';
      await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;});
      const data=new Uint8Array(262144);
      for(let i=0;i<data.length;i++)data[i]=i%251;
      const delay=[];
      for(let i=0;i<5;i++){
        const start=performance.now();
        await new Promise((r,j)=>{
          ws.onmessage=e=>e.data.byteLength===data.length?r():j(Error('echo length mismatch'));
          ws.send(data);
        });
        delay.push(performance.now()-start);
      }
      ws.close();
      return delay;
    });
    results.push({name,roundtripMs,stats});
    console.log(JSON.stringify(results.at(-1)));
  }finally{ await b.close(); }
}
fs.writeFileSync(out,JSON.stringify(results,null,2)+'\n');
