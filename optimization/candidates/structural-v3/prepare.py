"""Freeze a qualified integration and an independent corrected MIX probe."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIFO = ROOT / 'evidence/formal/tile-fifo-6ad335a8/source'
BASE = ROOT / 'evidence/formal/tile16-persistent-6ad31941/source'

def change(source, old, new):
    assert source.count(old) == 1, (old, source.count(old))
    return source.replace(old, new)

fifo = (FIFO / 'kernel.asc').read_text()
assert hashlib.sha256(fifo.encode()).hexdigest() == '427a35b31dbc75c3afbb8b1681c68f6c852b8f3b5620ca889c62c56f6083bef4'
combo = change(fifo, 'constexpr uint32_t VECTOR_TILE_N = 4096;', 'constexpr uint32_t VECTOR_TILE_N = 8192;')
combo = change(combo, '        pipe->InitBuffer(reduceWorkBuffer, VECTOR_TILE_N * sizeof(float));\n', '')
combo = change(combo, 'pipe->InitBuffer(quantHalfBuffer, VECTOR_TILE_N * sizeof(half));',
               'pipe->InitBuffer(quantHalfBuffer, VECTOR_TILE_N * sizeof(float));')
combo = change(combo, 'AscendC::LocalTensor<float> reduceWorkLocal = reduceWorkBuffer.Get<float>();',
               'AscendC::LocalTensor<float> reduceWorkLocal = divisorBuffer.Get<float>();')
combo = change(combo, 'auto denominatorLocal = reduceWorkBuffer.Get<float>();',
               'auto denominatorLocal = quantHalfBuffer.Get<float>();')
combo = change(combo, '    AscendC::TBuf<AscendC::QuePosition::VECCALC> reduceWorkBuffer;\n', '')

dual = (BASE / 'kernel.asc').read_text()
assert hashlib.sha256(dual.encode()).hexdigest() == 'cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae'
start = dual.index('__global__ __aicore__ void quant_mix_2d(')
end = dual.index('\ninline bool GenerateTileTiling', start)
body = change(dual[start:end], 'KERNEL_TYPE_MIX_AIC_1_1', 'KERNEL_TYPE_MIX_AIC_1_2')
body = change(body, '''        const uint32_t first = static_cast<uint64_t>(tiling.M) * block / blocks;
        const uint32_t end = static_cast<uint64_t>(tiling.M) * (block + 1U) / blocks;''', '''        // dav_c220 GetBlockIdxImpl already flattens AIV core and sub-block.
        const uint32_t vectorBlocks = blocks * AscendC::GetTaskRation();
        const uint32_t first = static_cast<uint64_t>(tiling.M) * block / vectorBlocks;
        const uint32_t end = static_cast<uint64_t>(tiling.M) * (block + 1U) / vectorBlocks;''')
dual = dual[:start] + body + dual[end:]
dual = change(dual, 'platform->GetCoreNumAiv()));', 'platform->GetCoreNumAiv() / 2U));')

for name, source, parent in [('fifo-ub8192', combo, FIFO), ('dual-aiv-corrected', dual, BASE)]:
    candidate = HERE / name
    project = candidate / 'submit-project'
    assert not project.exists(), project
    shutil.copytree(parent, project)
    (project / 'kernel.asc').write_text(source)
    hashes = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob('*') if p.is_file()}
    (candidate / 'project-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (candidate / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(structural_v3 LANGUAGES ASC CXX)
add_executable(bench_structural "${CMAKE_CURRENT_SOURCE_DIR}/../../../bench.asc")
target_compile_definitions(bench_structural PRIVATE BENCH_KERNEL="${CMAKE_CURRENT_SOURCE_DIR}/submit-project/kernel.asc")
target_compile_options(bench_structural PRIVATE $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(bench_structural PRIVATE tiling_api register platform unified_dlog dl m graph_base)
''')
    print(name, hashes['kernel.asc'])
