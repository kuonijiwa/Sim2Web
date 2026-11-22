from pathlib import Path
from shutil import move
from sys import argv
from vtkmodules.web.vtkjs_helper import addDataToViewer
scene,template,target=map(Path,argv[1:])
generated=scene.with_suffix(".html")
backup=scene.with_name("bundled_glance_backup.html")
if generated.exists():
    move(generated,backup)
try:
    addDataToViewer(str(scene),str(template))
    assert generated.is_file() and generated.stat().st_size>scene.stat().st_size
    move(generated,target)
finally:
    if backup.is_file():move(backup,generated)
print(target.stat().st_size)
