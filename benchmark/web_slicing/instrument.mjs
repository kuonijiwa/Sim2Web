import { spawn } from 'node:child_process';
import readline from 'node:readline';

export const throughput = { download: 20_000_000 / 8, upload: 5_000_000 / 8 };
export async function configureNetwork(page, cdp, network, websocket, shape=true) {
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', {cacheDisabled:true});
  if(network==='4G') await cdp.send('Network.emulateNetworkConditions', {
    offline:false, latency:50, downloadThroughput:throughput.download, uploadThroughput:throughput.upload,
    connectionType:'cellular4g'
  });
  const counters={httpBytes:0,incomingWsBytes:0,outgoingWsBytes:0,incomingFrames:0,outgoingFrames:0,framesDelayed:0,maxScheduledDelayMs:0};
  const timeline=[];
  let wallOffset;
  cdp.on('Network.requestWillBeSent',e=>{wallOffset ??= 1000*(e.wallTime-e.timestamp);});
  const at=ts=>wallOffset===undefined?Date.now():1000*ts+wallOffset;
  const note=(kind,bytes,ms)=>timeline.push({kind,bytes,ms});
  cdp.on('Network.loadingFinished',e=>{
    const bytes=e.encodedDataLength||0;
    counters.httpBytes+=bytes;
    note('httpBytes',bytes,at(e.timestamp));
  });
  if(websocket && shape){
    await page.routeWebSocket(/.*/, client=>{
      const upstream=client.connectToServer();
      let downNext=0;
      let upNext=0;
      function send(data, down){
        const bytes=Buffer.byteLength(data);
        const deliver=()=>{
          if(down){client.send(data); counters.incomingWsBytes+=bytes;counters.incomingFrames++;note('incomingWsBytes',bytes,Date.now());}
          else{upstream.send(data); counters.outgoingWsBytes+=bytes;counters.outgoingFrames++;note('outgoingWsBytes',bytes,Date.now());}
        };
        if(network!=='4G'){deliver();return;}
        const now=performance.now();
        const finish=Math.max(now,down?downNext:upNext)+1000*bytes/(down?throughput.download:throughput.upload);
        if(down)downNext=finish;else upNext=finish;
        const delay=25+finish-now;
        counters.framesDelayed++;
        counters.maxScheduledDelayMs=Math.max(counters.maxScheduledDelayMs,delay);
        setTimeout(deliver,Math.ceil(delay));
      }
      client.onMessage(data=>send(data,false));
      upstream.onMessage(data=>send(data,true));
    });
  } else if(websocket) {
    const bytes=r=>r.opcode===2?Buffer.byteLength(r.payloadData,'base64'):Buffer.byteLength(r.payloadData);
    cdp.on('Network.webSocketFrameReceived',e=>{const n=bytes(e.response);counters.incomingWsBytes+=n;counters.incomingFrames++;note('incomingWsBytes',n,at(e.timestamp));});
    cdp.on('Network.webSocketFrameSent',e=>{const n=bytes(e.response);counters.outgoingWsBytes+=n;counters.outgoingFrames++;note('outgoingWsBytes',n,at(e.timestamp));});
  }
  Object.defineProperty(counters,'upTo',{value:cutoff=>{
    const traffic={httpBytes:0,incomingWsBytes:0,outgoingWsBytes:0};
    for(const e of timeline)if(e.ms<=cutoff)traffic[e.kind]+=e.bytes;
    return traffic;
  }});
  return counters;
}

export async function sampler(python, file, serverPid) {
  const proc=spawn(python,[file,String(process.pid),String(serverPid||0)],{windowsHide:true});
  proc.stderr.on('data',d=>console.error(d.toString()));
  const lines=readline.createInterface({input:proc.stdout});
  const it=lines[Symbol.asyncIterator]();
  const hello=await it.next();
  if(hello.value!=='ready')throw Error('Could not start psutil sampler');
  return {async snapshot(){proc.stdin.write('snapshot\n'); return JSON.parse((await it.next()).value);},
    close(){proc.stdin.end('quit\n');lines.close();}};
}

// Arm a new frame before each slider input. Only qualifying geometry draws
// and decoded image draws on the actual large section canvas can complete it.
export function installPaintWatcher({remoteView=false,firstIndex}={}) {
  const tracker={epoch:1,queued:0,complete:null,target:firstIndex};
  tracker.arm=target=>{tracker.target=target;tracker.complete=null;tracker.queued=0;return ++tracker.epoch;};
  window.__r6Paint=tracker;
  const visible=canvas=>canvas?.width>=650 && canvas?.height>=400;
  function mark(canvas,kind,count,section){
    if(!visible(canvas)||tracker.queued===tracker.epoch)return;
    const epoch=tracker.epoch;
    tracker.queued=epoch;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(tracker.epoch===epoch)tracker.complete={epoch,kind,count,ms:performance.now(),...(section===undefined?{}:{section})};
    }));
  }
  function watch(proto,name,kind,judge){
    const prev=proto?.[name];
    if(!prev||prev.__r6)return;
    const fn=function(...args){
      const result=prev.apply(this,args);
      const count=judge(args);
      if(count)mark(this.canvas,kind,count);
      return result;
    };
    fn.__r6=true;
    proto[name]=fn;
  }
  if(!remoteView)for(const gl of [window.WebGLRenderingContext,window.WebGL2RenderingContext]){
    watch(gl?.prototype,'drawArrays','WebGL geometry',a=>a[0]===4 && a[2]>=36 ? a[2] : 0);
    watch(gl?.prototype,'drawElements','WebGL geometry',a=>a[0]===4 && a[1]>=36 ? a[1] : 0);
  }
  // vtkRemoteView displays server JPEGs in a visible background <img>.
  if(remoteView)document.addEventListener('load',e=>{
    const img=e.target;
    if(img instanceof HTMLImageElement && img.isConnected && img.naturalWidth>=650 && img.naturalHeight>=400
      && img.getBoundingClientRect().width>=650) {
      const probe=document.createElement('canvas');
      probe.width=probe.height=1;
      const ctx=probe.getContext('2d',{willReadFrequently:true});
      ctx.drawImage(img,16,img.naturalHeight-17,1,1,0,0,1,1);
      const [r,g,b]=ctx.getImageData(0,0,1,1).data;
      const index=Math.round((r-32)/21);
      if(index===tracker.target && Math.abs(g-40)<10 && Math.abs(b-100)<10){
        mark({width:img.naturalWidth,height:img.naturalHeight},'decoded server image',img.naturalWidth*img.naturalHeight,index);
      }
    }
  },true);
}
