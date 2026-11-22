// Performance instrumentation exposed at window.__SIM2WEB__.metrics so that
// browser-side load time, section switching latency, frame rate and memory can
// be measured reproducibly (see benchmark/browser_benchmark.mjs).

export class Metrics {
  constructor() {
    this.t0 = performance.timeOrigin;
    this.files = [];
    this.events = {};
    this.sectionSwitches = [];
    this.frameRates = [];
  }

  record(entry) {
    this.files.push({ at: performance.now(), ...entry });
  }

  mark(name) {
    this.events[name] = performance.now();
  }

  heap() {
    const m = performance.memory; // Chromium only
    return m ? { usedJSHeapSize: m.usedJSHeapSize, totalJSHeapSize: m.totalJSHeapSize } : null;
  }

  summary() {
    const fetched = this.files.filter((f) => !f.cached && !f.prefetch);
    return {
      events: this.events,
      startupFiles: fetched.filter((f) => f.at <= (this.events.firstRender ?? Infinity)).map((f) => ({ ...f })),
      startupBytes: fetched.filter((f) => f.at <= (this.events.firstRender ?? Infinity)).reduce((s, f) => s + f.bytes, 0),
      totalFetchedBytes: this.files.filter((f) => !f.cached).reduce((s, f) => s + f.bytes, 0),
      sectionSwitches: this.sectionSwitches,
      frameRates: this.frameRates,
      heap: this.heap(),
      userAgent: navigator.userAgent,
      devicePixelRatio: window.devicePixelRatio,
    };
  }
}

// Resolve after the browser has painted the current frame.
export function afterPaint() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}
