"""Independent architecture candidates from a verified, immutable baseline."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/tile16-persistent-6ad31941/source'
original = (BASE / 'kernel.asc').read_text()
assert hashlib.sha256(original.encode()).hexdigest() == 'cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae'

def replace(source, old, new, count=1):
    assert source.count(old) == count, (old, source.count(old))
    return source.replace(old, new)

dual = original
start = dual.index('__global__ __aicore__ void quant_mix_2d(')
end = dual.index('\ninline bool GenerateTileTiling', start)
body = dual[start:end]
body = replace(body, 'KERNEL_TYPE_MIX_AIC_1_1', 'KERNEL_TYPE_MIX_AIC_1_2')
body = replace(body, '''        const uint32_t first = static_cast<uint64_t>(tiling.M) * block / blocks;
        const uint32_t end = static_cast<uint64_t>(tiling.M) * (block + 1U) / blocks;''', '''        // AIV GetBlockIdx is the paired AIC index; sub-block selects its half.
        const uint32_t vectorBlock = block * 2U + AscendC::GetSubBlockIdx();
        const uint32_t vectorBlocks = blocks * 2U;
        const uint32_t first = static_cast<uint64_t>(tiling.M) * vectorBlock / vectorBlocks;
        const uint32_t end = static_cast<uint64_t>(tiling.M) * (vectorBlock + 1U) / vectorBlocks;''')
dual = dual[:start] + body + dual[end:]
dual = replace(dual, 'platform->GetCoreNumAiv()));', 'platform->GetCoreNumAiv() / 2U));')

wide = replace(original, 'constexpr uint32_t VECTOR_TILE_N = 4096;', '''// Phase-lifetime aliasing keeps 8192 FP32 activations within 192 KiB UB.
constexpr uint32_t VECTOR_TILE_N = 8192;''')
wide = replace(wide, '        pipe->InitBuffer(reduceWorkBuffer, VECTOR_TILE_N * sizeof(float));\n', '')
wide = replace(wide, 'pipe->InitBuffer(quantHalfBuffer, VECTOR_TILE_N * sizeof(half));', '''// Before the final int16 -> half cast this buffer is FP32 denominator scratch.
        pipe->InitBuffer(quantHalfBuffer, VECTOR_TILE_N * sizeof(float));''')
wide = replace(wide, 'AscendC::LocalTensor<float> reduceWorkLocal = reduceWorkBuffer.Get<float>();', 'AscendC::LocalTensor<float> reduceWorkLocal = divisorBuffer.Get<float>();')
wide = replace(wide, 'auto denominatorLocal = reduceWorkBuffer.Get<float>();', 'auto denominatorLocal = quantHalfBuffer.Get<float>();')
wide = replace(wide, '    AscendC::TBuf<AscendC::QuePosition::VECCALC> reduceWorkBuffer;\n', '')

for name, source in [('dual-aiv', dual), ('ub-resident-8192', wide)]:
    dest = HERE / name
    project = dest / 'submit-project'
    assert not project.exists(), project
    shutil.copytree(BASE, project)
    (project / 'kernel.asc').write_text(source)
    hashes = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob('*') if p.is_file()}
    (dest / 'project-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    (dest / 'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(structural_probe LANGUAGES ASC CXX)
add_executable(bench_structural "${CMAKE_CURRENT_SOURCE_DIR}/../../../bench.asc")
target_compile_definitions(bench_structural PRIVATE BENCH_KERNEL="${CMAKE_CURRENT_SOURCE_DIR}/submit-project/kernel.asc")
target_compile_options(bench_structural PRIVATE $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(bench_structural PRIVATE tiling_api register platform unified_dlog dl m graph_base)
''')
    print(name, hashes['kernel.asc'])
