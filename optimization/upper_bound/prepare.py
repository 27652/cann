#!/usr/bin/env python3
"""Freeze an isolated, runtime-dispatched ablation executable (no submission)."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def replace(source, old, new, count=1):
    if source.count(old) != count:
        raise ValueError(f"expected {count} occurrences: {old[:100]!r}")
    return source.replace(old, new)


def prepare():
    # Refuse to rewrite a frozen experiment. New identities require a new directory.
    dest = HERE / "source"
    dest.mkdir(exist_ok=False)
    baseline = (ROOT / "kernel.asc").read_text()
    (dest / "baseline.asc").write_text(baseline)
    s = baseline
    s = replace(s, "const CubeTiling &tilingData,\n                                AscendC::TPipe *pipe, bool useFloatMatmul = false)",
                "const CubeTiling &tilingData,\n                                AscendC::TPipe *pipe, bool useFloatMatmul = false,\n                                bool disableExact = false, uint32_t outputStride = 0)")
    s = replace(s, "floatMatmul = useFloatMatmul;", "floatMatmul = useFloatMatmul;\n        noExact = disableExact;\n        outStride = outputStride ? outputStride : tiling.N;")
    s = replace(s, "bool floatMatmul = false;", "bool floatMatmul = false;\n    bool noExact = false;\n    uint32_t outStride = 0;")
    # Keep the baseline mask/hint work; bypass scalar correction only. Fallback
    # rows additionally require RINT, rather than leaving FLOOR hints as output.
    s = replace(s, "if (useBoundaryMask || QUANT_VECTOR_ONLY) {", "if (useBoundaryMask || QUANT_VECTOR_ONLY || noExact) {")
    s = replace(s, "if (useBoundaryMask) {\n                    auto mask", "if (useBoundaryMask && !noExact) {\n                    auto mask")
    s = replace(s, "} else if (!QUANT_VECTOR_ONLY) {", "} else if (!QUANT_VECTOR_ONLY && !noExact) {")
    s = replace(s, "yGlobal[static_cast<uint64_t>(row) * tiling.N + column]", "yGlobal[static_cast<uint64_t>(row) * outStride + column]")
    s = replace(s, "GM_ADDR yScale, __kfc_workspace__ GM_ADDR workspace, CubeTiling tiling)",
                "GM_ADDR yScale, __kfc_workspace__ GM_ADDR workspace, CubeTiling tiling,\n    uint32_t mode, uint32_t globalN, uint32_t shardWidth)")
    s = replace(s, "const bool useFloatMatmul = tiling.Ka >= FP32_MATMUL_K_THRESHOLD;", "const bool useFloatMatmul = mode != 1U && tiling.Ka >= FP32_MATMUL_K_THRESHOLD;")
    s = replace(s, "&pipe, true);", "&pipe, true, mode == 2U);")
    # Synthetic N split: each group handles every row of a disjoint N interval.
    # Partial scales are private scratch; they are NOT claimed to be global scales.
    s = replace(s, "GM_ADDR mmWorkspace = workspace;", """GM_ADDR mmWorkspace = workspace;
    uint32_t outputStride = 0;
    if (mode == 4U) {
        const uint32_t shard = AscendC::GetBlockIdx();
        const uint32_t column = shard * shardWidth;
        const uint32_t validN = globalN - column < shardWidth ? globalN - column : shardWidth;
        x2 += static_cast<uint64_t>(column) * tiling.Kb;
        x2Scale += static_cast<uint64_t>(column) * sizeof(float);
        y += column;
        mmWorkspace += static_cast<uint64_t>(shard) * tiling.M * shardWidth * sizeof(int32_t);
        yScale = workspace + static_cast<uint64_t>(tiling.usedCoreNum) * tiling.M * shardWidth * sizeof(int32_t)
            + static_cast<uint64_t>(shard) * tiling.M * 32U;
        tiling.N = validN;
        // All groups now have local row ownership starting at zero. Their
        // Matmul service registration retains a separate physical block id.
        outputStride = globalN;
    }""")
    s = replace(s, "cubeStage.Init(x1, x2, mmWorkspace, tiling);", "cubeStage.Init(x1, x2, mmWorkspace, tiling, mode == 1U, mode == 4U);")
    s = replace(s, "vectorStage.Init(mmWorkspace, x1Scale, x2Scale, y, yScale, tiling, &pipe);", "vectorStage.Init(mmWorkspace, x1Scale, x2Scale, y, yScale, tiling, &pipe, false, mode == 2U, outputStride);")
    s = replace(s, "const CubeTiling &tilingData)\n    {\n        tiling = tilingData;", "const CubeTiling &tilingData, bool forceChunk = false, bool nSplit = false)\n    {\n        tiling = tilingData;\n        chunked = forceChunk;\n        splitN = nSplit;")
    s = replace(s, "const uint32_t rowOffset = cubeIdx * tiling.singleCoreM;", "const uint32_t rowOffset = splitN ? 0U : cubeIdx * tiling.singleCoreM;")
    s = replace(s, "if (tiling.Ka < FIRST_POSSIBLE_INT32_OVERFLOW_K) {", "if (!chunked && tiling.Ka < FIRST_POSSIBLE_INT32_OVERFLOW_K) {")
    s = replace(s, "uint32_t validRows = 0;\n\nprivate:", "uint32_t validRows = 0;\n    bool chunked = false;\n    bool splitN = false;\n\nprivate:")
    s = replace(s, "const uint32_t firstRow = cubeIdx * tiling.singleCoreM;", "const uint32_t firstRow = outStride != tiling.N ? 0U : cubeIdx * tiling.singleCoreM;")
    # Host side accepts mode via argv-controlled global; device receives it by value.
    s = replace(s, 'extern "C" void run_kernel(', 'static uint32_t upperBoundMode = 0;\n\nextern "C" void run_kernel(')
    s = replace(s, "const uint32_t targetRowsPerCore =", "const uint32_t mode = upperBoundMode;\n    const uint32_t targetRowsPerCore =")
    s = replace(s, "const bool useFloatMatmul =\n        K >= QuantMatmulReluQuant::FP32_MATMUL_K_THRESHOLD;", "const bool useFloatMatmul =\n        mode != 1U && K >= QuantMatmulReluQuant::FP32_MATMUL_K_THRESHOLD;")
    # Retain baseline tiling for modes 0/1/2; mode 1 explicitly INT8 type and
    # original full-K strides. SetTail(..., chunkK) bounds each Cube accumulation.
    s = replace(s, "const uint32_t blockDim = tiling.usedCoreNum;", """uint32_t shardWidth = 0;
    if (mode == 3U || mode == 4U) {
        if (K >= QuantMatmulReluQuant::FP32_MATMUL_K_THRESHOLD) return;
        const bool nSplit = mode == 4U;
        const uint32_t extent = nSplit ? N : M;
        const uint32_t alignment = nSplit ? 32U : 1U;
        const uint32_t width = QuantMatmulReluQuant::AlignUpHost(
            QuantMatmulReluQuant::CeilDivHost(extent, hardwareCores), alignment);
        const uint32_t groups = QuantMatmulReluQuant::CeilDivHost(extent, width);
        const uint32_t localM = nSplit ? M : width;
        const uint32_t localN = nSplit ? width : N;
        if (!QuantMatmulReluQuant::GenerateMatmulTiling(platform, localM, localN, K,
            1U, std::min(128U, QuantMatmulReluQuant::AlignUpHost(localM, 16U)),
            std::min(256U, QuantMatmulReluQuant::AlignUpHost(localN, 16U)), false, tiling)) return;
        if (tiling.singleCoreM < localM || tiling.singleCoreN < localN) return;
        tiling.M = M;
        tiling.usedCoreNum = groups;
        if (!nSplit) tiling.singleCoreM = width;
        shardWidth = nSplit ? width : 0U;
    }
    const uint32_t blockDim = tiling.usedCoreNum;""")
    s = replace(s, "const uint64_t totalWorkspaceSize = userWorkspaceOffset + matrixWorkspaceSize;", """if (mode == 4U) matrixWorkspaceSize = static_cast<uint64_t>(blockDim) * M *
        (static_cast<uint64_t>(shardWidth) * sizeof(int32_t) + 32U);
    const uint64_t totalWorkspaceSize = userWorkspaceOffset + matrixWorkspaceSize;
    std::fprintf(stderr, "ABLATION mode=%u cores=%u singleM=%u N=%u K=%u workspace=%llu\\n",
        mode, blockDim, tiling.singleCoreM, tiling.N, tiling.Ka,
        static_cast<unsigned long long>(totalWorkspaceSize));""")
    s = replace(s, "x1, x2, x1Scale, x2Scale, y, yScale, workspace, tiling);", "x1, x2, x1Scale, x2Scale, y, yScale, workspace, tiling, mode, N, shardWidth);")
    (dest / "kernel.asc").write_text(s)
    bench = (ROOT / "optimization/bench.asc").read_text()
    bench = replace(bench, '#define BENCH_KERNEL "../kernel.asc"', '#define BENCH_KERNEL "kernel.asc"')
    bench = replace(bench, "if (argc != 4) return 1;", "if (argc != 5) return 1;\n    upperBoundMode = std::strtoul(argv[4], nullptr, 10);\n    if (upperBoundMode > 4U) return 1;")
    (dest / "bench.asc").write_text(bench)
    (dest / "CMakeLists.txt").write_text('''cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(upper_bound LANGUAGES ASC CXX)
add_executable(bench_upper_bound bench.asc)
target_compile_options(bench_upper_bound PRIVATE $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(bench_upper_bound PRIVATE tiling_api register platform unified_dlog dl m graph_base)
''')
    identity = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in dest.iterdir()}
    (HERE / "source-identity.json").write_text(json.dumps(identity, indent=2) + "\n")


if __name__ == "__main__":
    prepare()
