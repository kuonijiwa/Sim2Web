import hashlib,zipfile,sys
from pathlib import Path
root=Path(sys.argv[1])
dest=root/"codex_run_2026-11-21_r4_evidence.zip"
manifest=dict()
for f in sorted(root.rglob("*")):
    if not f.is_file() or f==dest or f.name=="EVIDENCE_SHA256.txt":
        continue
    rel=f.relative_to(root)
    assert not set(rel.parts).intersection({"site","model_cache",".git","node_modules"}),rel
    assert f.suffix.lower() not in (".vtu",".vtp",".e",".odb",".vtkjs",".html"),rel
    assert f.stat().st_size<7_000_000,rel
    manifest[rel.as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
m=root/"EVIDENCE_SHA256.txt"
m.write_text("".join(f"{digest}  {rel}\n" for rel,digest in manifest.items()),encoding="utf-8")
with zipfile.ZipFile(dest,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for rel in manifest:
        z.write(root/rel,rel)
    z.write(m,m.name)
with zipfile.ZipFile(dest) as z:
    assert z.testzip() is None
    assert len(z.namelist())==len(manifest)+1
    for rel,digest in manifest.items():
        assert hashlib.sha256(z.read(rel)).hexdigest()==digest,rel
print(dest)
print("entries",len(manifest)+1,"bytes",dest.stat().st_size,"sha256",hashlib.sha256(dest.read_bytes()).hexdigest())
