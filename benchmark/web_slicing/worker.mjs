import { unpack, makeIndex, cut } from './cutter.mjs';

let mesh;
let index;
self.onmessage = async ({data}) => {
  try {
    if (data.type === 'load') {
      const start = performance.now();
      mesh = unpack(data.buffer);
      const parsed = performance.now();
      index = makeIndex(mesh);
      self.postMessage({type:'ready', timings:{parse:parsed-start,index:performance.now()-parsed}});
    } else {
      const start = performance.now();
      const geometry = cut(mesh, index, data.x);
      self.postMessage({type:'section', ms:performance.now()-start, ...geometry},
        [geometry.points.buffer,geometry.polys.buffer,geometry.values.buffer]);
    }
  } catch (error) {self.postMessage({type:'error',error:String(error)});}
};
