"""Explicit A1-resident four-N-tile reuse, based only on official dual AIV."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/dual-aiv-fixed-6ad33b78/source'
s = (BASE / 'kernel.asc').read_text()
assert hashlib.sha256(s.encode()).hexdigest() == 'bae4d14b3b7eaa918034a8f0bde94bfa49ce38dc2c992d9e7d7326c50ac9fc95'
start = s.index('__global__ __aicore__ void quant_mix_2d(')
end = s.index('\ninline bool GenerateTileTiling', start)
kernel = s[start:end].replace('void quant_mix_2d(', 'void quant_mix_l1(')
kernel = kernel.replace('TPosition::GM, CubeFormat::ND, int8_t, false>',
                        'TPosition::A1, CubeFormat::NZ, int8_t, false>')
old = kernel[kernel.index('        const uint64_t taskCount'):kernel.index('        mm.End();')]
new = '''        // Four adjacent N tiles share one explicitly staged A panel.
        // Supported dispatch: K multiple of 32, K<=4096; A uses <=64KiB L1.
        AscendC::TBuf<AscendC::TPosition::A1> aBuffer;
        pipe.InitBuffer(aBuffer, tileM * tiling.Ka);
        auto aLocal = aBuffer.Get<int8_t>();
        const uint32_t groupsN = (nTiles + 3U) / 4U;
        const uint64_t taskCount = static_cast<uint64_t>(mTiles) * groupsN;
        for (uint64_t task = block; task < taskCount; task += blocks) {
            const uint32_t row = (task % mTiles) * tileM;
            const uint32_t firstN = (task / mTiles) * 4U;
            const uint32_t rows = tiling.M - row < tileM ? tiling.M - row : tileM;
            AscendC::Nd2NzParams copy;
            copy.ndNum = 1;
            copy.nValue = rows;
            copy.dValue = tiling.Ka;
            copy.srcDValue = tiling.Ka;
            copy.dstNzC0Stride = tileM;
            copy.dstNzNStride = 1;
            AscendC::DataCopy(aLocal, a[static_cast<uint64_t>(row) * tiling.Ka], copy);
            const auto ready = pipe.FetchEventID(AscendC::HardEvent::MTE2_MTE1);
            AscendC::SetFlag<AscendC::HardEvent::MTE2_MTE1>(ready);
            AscendC::WaitFlag<AscendC::HardEvent::MTE2_MTE1>(ready);
            for (uint32_t nt = firstN; nt < nTiles && nt < firstN + 4U; ++nt) {
                const uint32_t col = nt * tileN;
                const uint32_t cols = tiling.N - col < tileN ? tiling.N - col : tileN;
                mm.SetSingleShape(rows, cols, tiling.Ka);
                mm.SetTensorA(aLocal, false);
                mm.SetTensorB(b[static_cast<uint64_t>(col) * tiling.Kb], true);
                mm.template IterateAll<true>(c[static_cast<uint64_t>(row) * tiling.N + col]);
            }
            // No next GM->L1 staging until all current L1 consumers complete.
            const auto free = pipe.FetchEventID(AscendC::HardEvent::MTE1_MTE2);
            AscendC::SetFlag<AscendC::HardEvent::MTE1_MTE2>(free);
            AscendC::WaitFlag<AscendC::HardEvent::MTE1_MTE2>(free);
        }
'''
kernel = kernel.replace(old, new)
s = s[:end] + '\n' + kernel + s[end:]
s = s.replace('uint32_t tileM, uint32_t tileN, CubeTiling &tiling)\n',
              'uint32_t tileM, uint32_t tileN, CubeTiling &tiling, bool useL1 = false)\n')
old = '''    api.SetAType(matmul_tiling::TPosition::GM, matmul_tiling::CubeFormat::ND,
                 matmul_tiling::DataType::DT_INT8, false);'''
assert s.count(old) == 1
s = s.replace(old, '''    api.SetAType(useL1 ? matmul_tiling::TPosition::A1 : matmul_tiling::TPosition::GM,
                 useL1 ? matmul_tiling::CubeFormat::NZ : matmul_tiling::CubeFormat::ND,
                 matmul_tiling::DataType::DT_INT8, false);''')
old = '    QuantMatmulReluQuant::CubeTiling tileTiling;'
s = s.replace(old, '''    const bool useL1 = K <= 4096U && K % 32U == 0U && N > tileN;
''' + old, 1)
s = s.replace('GenerateTileTiling(platform, M, N, K, tileM, tileN, tileTiling)',
              'GenerateTileTiling(platform, M, N, K, tileM, tileN, tileTiling, useL1)')
old = '    QuantMatmulReluQuant::quant_mix_2d<<<cubeBlocks, nullptr, stream>>>('
s = s.replace(old, '''    if (useL1) {
        QuantMatmulReluQuant::quant_mix_l1<<<cubeBlocks, nullptr, stream>>>(
            x1, x2, scratch, x1Scale, x2Scale, y, yScale, tileTiling, tileM, tileN);
    } else
''' + old)
for name, content in [('baseline', (BASE/'kernel.asc').read_text()), ('a-l1-group4', s)]:
    dest = HERE / name / 'submit-project'
    assert not dest.exists(), dest
    shutil.copytree(BASE, dest)
    (dest/'kernel.asc').write_text(content)
    hashes = {p.relative_to(dest).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in dest.rglob('*') if p.is_file()}
    (dest.parent/'project-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    (dest.parent/'CMakeLists.txt').write_text('''cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(dual_aiv_l1 LANGUAGES ASC CXX)
add_executable(bench_l1 "${CMAKE_CURRENT_SOURCE_DIR}/../../../bench.asc")
target_compile_definitions(bench_l1 PRIVATE BENCH_KERNEL="${CMAKE_CURRENT_SOURCE_DIR}/submit-project/kernel.asc")
target_compile_options(bench_l1 PRIVATE $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(bench_l1 PRIVATE tiling_api register platform unified_dlog dl m graph_base)
''')
    print(name, hashes['kernel.asc'])
