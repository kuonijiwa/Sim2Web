// Client of the local workbench server (src/sim2web/workbench.py).

async function request(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `${res.status} ${res.statusText}`);
  return data;
}

export const api = {
  project: () => request('GET', '/api/project'),
  saveConfig: (config) => request('PUT', '/api/config', { config }),
  browse: (path) => request('GET', `/api/browse${path ? `?path=${encodeURIComponent(path)}` : ''}`),
  startJob: (kind, params = {}) => request('POST', '/api/jobs', { kind, params }),
  job: (id, since = 0) => request('GET', `/api/jobs/${id}?since=${since}`),
};

// Run a job to completion, passing new log lines to `onLog`.
export async function runJob(kind, params, onLog, interval = 400) {
  const started = await api.startJob(kind, params);
  let since = 0;
  for (;;) {
    const view = await api.job(started.id, since);
    if (view.log.length) onLog(view.log);
    since = view.log_length;
    if (view.state !== 'running') {
      if (view.state === 'failed') throw new Error(view.error || `${kind} failed`);
      return view;
    }
    await new Promise((r) => setTimeout(r, interval));
  }
}
