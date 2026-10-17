"""Create independent corrected ownership and L0C diagnostic probes."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/tile16-persistent-6ad31941/source'

dual = (ROOT / 'optimization/candidates/structural-breakthrough-v2/dual-aiv/submit-project/kernel.asc').read_text()
old = 'const uint32_t vectorBlock = block * 2U + AscendC::GetSubBlockIdx();'
assert dual.count(old) == 1
dual = dual.replace(old, 'const uint32_t vectorBlock = block;')
dual = dual.replace('// AIV GetBlockIdx is the paired AIC index; sub-block selects its half.',
                    '// On dav-2201 AIV GetBlockIdx already includes the sub-block index.')

local = (ROOT / 'optimization/candidates/architecture-trials-v1/local-k/kernel.asc').read_text()
start = local.index('__global__ __aicore__ void quant_mix_2d(')
end = local.index('\ninline bool GenerateTileTiling', start)
body = local[start:end]
body = body.replace('const uint32_t chunk = tiling.Ka - k < SAFE_ACCUM_K\n'
                    '                    ? tiling.Ka - k : SAFE_ACCUM_K;',
                    'const uint32_t chunk = tiling.Ka - k < 64U\n'
                    '                    ? tiling.Ka - k : 64U;')
body = body.replace('tiling.Ka > SAFE_ACCUM_K &&', 'tiling.Ka > 64U &&')
assert 'const uint32_t chunk = tiling.Ka - k < 64U' in body
local = local[:start] + body + local[end:]

for name, source in (('dual-aiv-fixed', dual), ('l0c-chunk64-probe', local)):
    dest = HERE / name
    project = dest / 'submit-project'
    project.mkdir(parents=True, exist_ok=False)
    # Copy only the eight known project files, not incidental old bundle backups.
    files = json.loads((BASE.parent / 'evidence.json').read_text())['files']
    for filename in files:
        path = project / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((BASE / filename).read_bytes())
    (project / 'kernel.asc').write_text(source)
    hashes = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob('*') if p.is_file()}
    (dest / 'project-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (dest / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(ownership_l0c_probe LANGUAGES ASC CXX)
add_executable(bench_probe "${CMAKE_CURRENT_SOURCE_DIR}/../../../wide-row-tile-cv/bench.asc")
target_compile_definitions(bench_probe PRIVATE BENCH_KERNEL="${CMAKE_CURRENT_SOURCE_DIR}/submit-project/kernel.asc")
target_compile_options(bench_probe PRIVATE $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(bench_probe PRIVATE tiling_api register platform unified_dlog dl m graph_base)
'''.replace('../../../wide-row', '../../wide-row'))
    print(name, hashes['kernel.asc'])
