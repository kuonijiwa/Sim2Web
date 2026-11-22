# Deployment on IIS and other static servers

A package built by `sim2web build case.yaml` is a self-contained static site:

```text
site/
  index.html
  assets/            viewer JavaScript and CSS (content-hashed names)
  model_cache/
    index.json       package index
    <stage>/...vtp   surfaces and sections
```

Copy the whole `site/` directory to any static web server; no server-side
runtime is needed. Opening `index.html` through `file://` does not work because
browsers block the data requests; use `sim2web serve site` locally.

## IIS

Enable **Static Content** and add MIME mappings if missing:

| Extension | MIME type |
|---|---|
| `.vtp` | `application/octet-stream` |
| `.json` | `application/json` |

Enable **dynamic/static compression** for `.vtp` if desired: VTP products are
already zlib-compressed internally, so the additional gain is usually small,
but it can be measured with `benchmark/browser_benchmark.mjs --gzip`.

Hashed files in `assets/` can be cached for a long time. Use short caching, or
deploy each package version to a new path, for `model_cache/`.

## Checks after deployment

1. The first model appears without errors (status line reads "Ready").
2. The browser console shows no 404, MIME or CORS errors.
3. Changing the field updates colours and legend; the badge shows cell or point data.
4. Sections switch with the slider; "Package and performance" lists the transfer sizes.
5. Clicking a surface shows `Source_Cell_ID` and values.

If a `.vtp` request returns 404, check case-sensitive file names and that
`model_cache/` is beside `index.html`. If data download but parsing fails,
check that Git LFS files were pulled rather than left as pointer text.
