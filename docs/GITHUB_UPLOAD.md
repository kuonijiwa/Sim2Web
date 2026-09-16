# Uploading SimWebView

## Before public upload

This is a prepared local candidate, not a published release. The owner approved
MIT for code, CC BY 4.0 for example data, and the copyright name HydroChina Itasca.
Software citation authors are recorded separately in `CITATION.cff`.
The confirmed repository is https://github.com/kuonijiwa/SimWebView. The owner
has aligned the repository name with the software display name.
No public commit, release date or archive DOI is asserted before publication.

The upload root is the directory containing `README.md`, `pyproject.toml`,
`package.json`, `src/`, `tests/` and `examples/`. Do not upload the surrounding
research workspace, archive ZIP, packaging manifests or local check directory.
The article itself is not part of this code bundle.

## Large files

The three source VTUs, retained VTP products and image evidence are included as
actual files. They are not LFS pointers yet. The supplied `.gitattributes` routes
these types through Git LFS when added to a Git repository with LFS installed.

Use Git and Git LFS, not the browser's file-upload page. GitHub's documented
browser limit is 25 MiB per file and its ordinary Git limit is 100 MiB per file;
the largest source model exceeds both. Keep `.gitattributes` in the commit.

Sources checked on 2026-09-10: [GitHub large-file limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
and [configuring Git LFS](https://docs.github.com/en/repositories/working-with-files/managing-large-files/configuring-git-large-file-storage).
Check the destination account's LFS storage and bandwidth allowance before use.

## First upload

First inspect the existing target repository:

```bash
git ls-remote https://github.com/kuonijiwa/SimWebView.git
```

A successful command with no refs indicates an empty repository. A network or
authentication error does not establish that it is empty. The commands below
apply only to an empty remote. If commits already exist, use the alternative
workflow below. Open a terminal in this prepared repository directory.
The following commands are instructions only; packaging has not executed them:

```bash
git init -b main
git lfs install --local
git add .gitattributes
git add .
git lfs ls-files
git diff --cached --stat
```

Inspect the staged files. Large VTU/VTP files must appear in the LFS listing.
There should be exactly three real case folders and no dependencies or caches.
Then commit using your own configured Git identity:

```bash
git commit -m "Prepare SimWebView three-case publication package"
git remote add origin https://github.com/kuonijiwa/SimWebView.git
git push -u origin main
```

Do not put access tokens or
passwords into a URL, script or committed file. Use your existing Git credential
manager. The npm `private: true` field prevents accidental npm publication; it
does not prevent GitHub hosting.

## If the remote already contains commits

Clone it into a separate working directory first. Preserve and review existing
files; copy the prepared package contents into that checkout without replacing
its `.git` directory. Install LFS filters before staging:

```bash
git clone https://github.com/kuonijiwa/SimWebView.git
cd SimWebView
git lfs install --local
git lfs pull
git status
```

After copying and reviewing the package, stage the files, inspect the staged
diff and `git lfs ls-files`, commit and push the checked-out branch. Do not
force-push or discard remote history to make an upload succeed.

## Check the uploaded version

Clone into another empty folder, fetch LFS assets, and run:

```bash
git lfs pull
python -m pip install -r requirements.txt
python -m pytest -q
npm ci
npm run build
```

The included VTP outputs allow inspection without rerunning processing. To
regenerate them or repeat the complete numerical comparison, follow the main
README and `docs/PUBLICATION_REVISION.md`; these commands overwrite generated
products and evidence. Assign a release tag and archive DOI only to an actual,
reviewed public version. Add real release identifiers to `CITATION.cff` after
they exist. The manuscript is managed separately and is not changed by this
package preparation or upload.
