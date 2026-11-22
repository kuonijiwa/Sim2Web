// Fetching and parsing VTP products with timing, transfer accounting and an LRU cache.
import vtkXMLPolyDataReader from '@kitware/vtk.js/IO/XML/XMLPolyDataReader';

export class ProductLoader {
  constructor({ capacity = 24, metrics }) {
    this.capacity = capacity;
    this.cache = new Map(); // url -> Promise<polydata>
    this.metrics = metrics;
  }

  has(url) {
    return this.cache.has(url);
  }

  load(url, { role = 'product', prefetch = false } = {}) {
    if (this.cache.has(url)) {
      const hit = this.cache.get(url);
      this.cache.delete(url);
      this.cache.set(url, hit); // refresh LRU position
      if (!prefetch) this.metrics.record({ url, role, cached: true, bytes: 0, fetchMs: 0, parseMs: 0 });
      return hit;
    }
    const task = this.#fetchAndParse(url, role, prefetch);
    this.cache.set(url, task);
    task.catch(() => this.cache.delete(url));
    while (this.cache.size > this.capacity) this.cache.delete(this.cache.keys().next().value);
    return task;
  }

  async #fetchAndParse(url, role, prefetch) {
    const t0 = performance.now();
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status} for ${url}`);
    const buffer = await response.arrayBuffer();
    const t1 = performance.now();
    const reader = vtkXMLPolyDataReader.newInstance();
    reader.parseAsArrayBuffer(buffer);
    const polydata = reader.getOutputData(0);
    polydata.buildCells?.();
    const t2 = performance.now();
    // Bytes actually transferred (compressed by the server) where the browser reports them.
    const entry = performance.getEntriesByName(new URL(url, window.location.href).href).pop();
    this.metrics.record({
      url, role, prefetch, cached: false, bytes: buffer.byteLength,
      transferBytes: entry?.transferSize || null, fetchMs: t1 - t0, parseMs: t2 - t1,
      points: polydata.getNumberOfPoints(), cells: polydata.getNumberOfCells(),
    });
    return polydata;
  }
}
