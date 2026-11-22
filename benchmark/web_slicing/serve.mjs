import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { gzipSync } from 'node:zlib';

const mime = {
  '.html':'text/html; charset=utf-8', '.js':'text/javascript', '.mjs':'text/javascript',
  '.css':'text/css', '.json':'application/json', '.vtp':'application/octet-stream',
};
export const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
export const launchOptions = {executablePath:chrome,headless:false,args:['--ignore-gpu-blocklist',
  '--enable-unsafe-swiftshader','--disable-background-timer-throttling','--enable-precise-memory-info']};

export async function staticServer(root, {data, output, gzip=true, overlays={}} = {}) {
  root = path.resolve(root);
  const compressed = new Map();
  const server = http.createServer((req,res)=>{
    const route = new URL(req.url,'http://127.0.0.1').pathname;
    if (output && req.method==='POST' && /^\/result\/[0-9]+$/.test(route)) {
      const file=path.join(output,'browser_' + route.split('/').at(-1) + '.bin');
      const stream=fs.createWriteStream(file);
      req.pipe(stream);
      stream.on('finish',()=>res.writeHead(200).end());
      return;
    }
    if (Object.hasOwn(overlays, route)) {
      if (!compressed.has(route)) {
        const input = Buffer.from(overlays[route]);
        compressed.set(route, gzip ? gzipSync(input, {level:6}) : input);
      }
      const bytes = compressed.get(route);
      const headers = {'Content-Type':mime[path.extname(route)],'Cache-Control':'no-store','Content-Length':bytes.length};
      if (gzip) headers['Content-Encoding'] = 'gzip';
      res.writeHead(200,headers).end(bytes);
      return;
    }
    let file;
    let encoded = false;
    if(data && route==='/volume.bin'){
      file=path.join(data,'volume.bin.gz');
      encoded=true;
    } else if(data && route==='/case.json') {
      file=path.join(data,'case.json');
    } else {
      file=path.resolve(root,'.'+(route==='/'?'/index.html':decodeURIComponent(route)));
      if(path.relative(root,file).startsWith('..')){res.writeHead(403).end();return;}
    }
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {res.writeHead(404).end();return;}
    const headers={'Content-Type':mime[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'};
    if(encoded){
      headers['Content-Encoding']='gzip';
      headers['Content-Length']=fs.statSync(file).size;
      res.writeHead(200,headers);
      fs.createReadStream(file).pipe(res);
      return;
    }
    if(gzip && !compressed.has(file)) compressed.set(file,gzipSync(fs.readFileSync(file),{level:6}));
    const bytes = gzip ? compressed.get(file) : fs.readFileSync(file);
    if(gzip) headers['Content-Encoding']='gzip';
    headers['Content-Length']=bytes.length;
    res.writeHead(200,headers).end(bytes);
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  return {url:'http://127.0.0.1:'+server.address().port,close:()=>server.close()};
}
