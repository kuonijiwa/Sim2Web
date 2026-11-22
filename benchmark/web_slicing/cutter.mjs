const edgeTables = {
  10: [[0,1],[1,2],[2,0],[0,3],[1,3],[2,3]],
  11: [[0,1],[1,3],[3,2],[2,0],[4,5],[5,7],[7,6],[6,4],[0,4],[1,5],[2,6],[3,7]],
  12: [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]],
  13: [[0,1],[1,2],[2,0],[3,4],[4,5],[5,3],[0,3],[1,4],[2,5]],
  14: [[0,1],[1,2],[2,3],[3,0],[0,4],[1,4],[2,4],[3,4]],
};

export function unpack(buffer) {
  const h = new Int32Array(buffer, 0, 4);
  if (h[0] !== 0x36574153) throw Error('Unexpected binary header');
  const [, pointCount, cellCount, connections] = h;
  let next = 16;
  const take = (Type, count) => {
    const array = new Type(buffer, next, count);
    next += count * Type.BYTES_PER_ELEMENT;
    return array;
  };
  const xyz = take(Float32Array, pointCount * 3);
  const offsets = take(Int32Array, cellCount + 1);
  const conn = take(Int32Array, connections);
  const types = take(Int32Array, cellCount);
  const vectors = take(Float32Array, pointCount * 3);
  const retained = take(Int32Array, cellCount);
  if (next !== buffer.byteLength) throw Error('Unexpected binary length');
  const magnitude = new Float32Array(pointCount);
  for (let i = 0; i < pointCount; i++) {
    const k = 3 * i;
    magnitude[i] = Math.hypot(vectors[k], vectors[k+1], vectors[k+2]);
  }
  return { xyz, offsets, conn, types, magnitude, retained, cellCount };
}

export function makeIndex(mesh) {
  const { xyz, offsets, conn, retained, cellCount } = mesh;
  const lo = new Float32Array(cellCount);
  const hi = new Float32Array(cellCount);
  let min = Infinity;
  let max = -Infinity;
  for (let c = 0; c < cellCount; c++) {
    if (!retained[c]) continue;
    let a = Infinity;
    let b = -Infinity;
    for (let k = offsets[c]; k < offsets[c+1]; k++) {
      const x = xyz[3 * conn[k]];
      if (x < a) a = x;
      if (x > b) b = x;
    }
    lo[c] = a;
    hi[c] = b;
    if (a < min) min = a;
    if (b > max) max = b;
  }
  const size = 128;
  const bucket = x => Math.min(size-1, Math.max(0, Math.floor((x-min)/(max-min)*size)));
  const counts = new Uint32Array(size);
  for (let c = 0; c < cellCount; c++) {
    if (!retained[c]) continue;
    for (let n = bucket(lo[c]), end = bucket(hi[c]); n <= end; n++) counts[n]++;
  }
  const buckets = Array.from(counts, n => new Uint32Array(n));
  counts.fill(0);
  for (let c = 0; c < cellCount; c++) {
    if (!retained[c]) continue;
    for (let n = bucket(lo[c]), end = bucket(hi[c]); n <= end; n++) buckets[n][counts[n]++] = c;
  }
  return { lo, hi, bucket, buckets };
}

export function cut(mesh, index, x) {
  const { xyz, offsets, conn, types, magnitude } = mesh;
  const pt = [];
  const values = [];
  const polys = [];
  const candidates = index.buckets[index.bucket(x)];
  for (const c of candidates) {
    // Use the VTK contour sign convention: zero belongs to the high side.
    if (index.lo[c] >= x || index.hi[c] < x) continue;
    const edges = edgeTables[types[c]];
    if (!edges) throw Error('Unsupported VTK cell type: ' + types[c]);
    const local = offsets[c];
    const crosses = [];
    let cy = 0;
    let cz = 0;
    for (const [j,k] of edges) {
      const a = conn[local+j];
      const b = conn[local+k];
      const pa = 3*a;
      const pb = 3*b;
      const ax = xyz[pa];
      const bx = xyz[pb];
      if ((ax >= x) === (bx >= x)) continue;
      const u = (x-ax)/(bx-ax);
      const y = xyz[pa+1] + (xyz[pb+1]-xyz[pa+1])*u;
      const z = xyz[pa+2] + (xyz[pb+2]-xyz[pa+2])*u;
      if (crosses.some(p => Math.abs(p[0]-y)<=1e-9 && Math.abs(p[1]-z)<=1e-9)) continue;
      crosses.push([y,z,magnitude[a]+(magnitude[b]-magnitude[a])*u,0]);
      cy += y;
      cz += z;
    }
    const n = crosses.length;
    if (n < 3) continue;
    for (const p of crosses) p[3] = Math.atan2(p[1]-cz/n,p[0]-cy/n);
    crosses.sort((a,b)=>a[3]-b[3]);
    const base = values.length;
    for (const [y,z,v] of crosses) {
      pt.push(x,y,z);
      values.push(v);
    }
    for (let j=1;j<n-1;j++) {
      const [ay,az] = crosses[0];
      const [by,bz] = crosses[j];
      const [cy2,cz2] = crosses[j+1];
      if (Math.abs((by-ay)*(cz2-az)-(bz-az)*(cy2-ay)) > 1e-14) polys.push(3,base,base+j,base+j+1);
    }
  }
  return {points:new Float32Array(pt), values:new Float32Array(values), polys:new Uint32Array(polys)};
}
