"""Keep the first compile intact; create a physically consistent A1 revision."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
source = HERE / 'a-l1-group4'
dest = HERE / 'a-l1-group4-stride16'
assert not dest.exists(), dest
shutil.copytree(source / 'submit-project', dest / 'submit-project')
shutil.copyfile(source / 'CMakeLists.txt', dest / 'CMakeLists.txt')
p = dest / 'submit-project/kernel.asc'
s = p.read_text()
start = s.index('__global__ __aicore__ void quant_mix_l1(')
end = s.index('\ninline bool GenerateTileTiling', start)
k = s[start:end]
old = 'mm.SetOrgShape(tiling.M, tiling.N, tiling.Ka, tiling.Kb);'
assert k.count(old) == 1
k = k.replace(old, 'mm.SetOrgShape(tileM, tiling.N, tiling.Ka, tiling.Kb);')
s = s[:start] + k + s[end:]
p.write_text(s)
hashes = {p.relative_to(dest / 'submit-project').as_posix():
          hashlib.sha256(p.read_bytes()).hexdigest()
          for p in (dest / 'submit-project').rglob('*') if p.is_file()}
(dest / 'project-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
print(hashes['kernel.asc'])
