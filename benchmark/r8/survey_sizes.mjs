import fs from 'node:fs/promises';
import http from 'node:http';
import path from 'node:path';

const [directory] = process.argv.slice(2);
const index = JSON.parse(await fs.readFile(path.join(directory,'index.json'),'utf8'));
const page = JSON.parse(await fs.readFile(path.join(directory,'stage_list.json'),'utf8'));
const target = path.join(directory,'file_sizes.json');
const previous = await fs.readFile(target,'utf8').then(JSON.parse,error=>{
  if(error.code==='ENOENT')return [];
  throw error;
});
const saved = new Map(previous.flatMap(stage=>stage.records.filter(x=>Number.isInteger(x.bytes)).map(x=>[x.file,x])));
const output = [];
let nextRequest = 0;
async function head(url) {
  const delay = Math.max(0,nextRequest-Date.now());
  if (delay) await new Promise(resolve=>setTimeout(resolve,delay));
  nextRequest=Date.now()+500;
  return new Promise((resolve,reject)=>{
    const request=http.request(url,{method:'HEAD',agent:false,headers:{Connection:'close'}},response=>{
      response.resume();
      const header=response.headers['content-length'];
      const status=response.statusCode;
      resolve({status,bytes:status===200 && header ? Number(header):null});
    });
    request.setTimeout(6000,()=>request.destroy(new Error('HEAD response timeout')));
    request.on('error',reject);
    request.end();
  });
}
for (const [id, stage] of Object.entries(index)) {
  const expected = [stage.cavity,...Object.values(stage.slices).flat()];
  const records = [];
  // A single HEAD at a time, and at most two starts per second. No asset bodies.
  for (const file of expected) {
    if(saved.has(file)){records.push(saved.get(file));continue;}
    const url = new URL(file,page.page);
    if (url.origin !== new URL(page.page).origin) throw Error('Asset leaves the surveyed site');
    const result=await head(url).catch(()=>head(url)).catch(error=>({bytes:null,error:String(error),cause:error.code ?? null}));
    records.push({file,...result});
    if (records.length === 1 && [405,429,503].includes(result.status)) break;
  }
  const valid = row => Number.isInteger(row.bytes);
  output.push({id,expectedFiles:expected.length,measuredFiles:records.filter(valid).length,
    surfaceBytes:records[0].bytes,sectionsBytes:records.length === expected.length && records.slice(1).every(valid)
      ? records.slice(1).reduce((n,row)=>n+row.bytes,0):null,records});
  await fs.writeFile(target,JSON.stringify([...output,...previous.filter(x=>!output.some(y=>y.id===x.id))],null,2)+'\n');
  console.log(`${id}: ${output.at(-1).measuredFiles}/${expected.length} size headers`);
}
