"""Create new isolated prototypes; refuse to overwrite any existing source."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
base = (ROOT / 'evidence/formal/tile16-persistent-6ad31941/source/kernel.asc').read_text()
assert hashlib.sha256(base.encode()).hexdigest() == 'cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae'


def replace_once(s, old, new):
    assert s.count(old) == 1, old[:100]
    return s.replace(old, new)


def emit(name, source):
    dest = HERE / name
    dest.mkdir(exist_ok=True)
    if (dest / 'kernel.asc').exists():
        assert (dest / 'kernel.asc').read_text() == source, name + ': existing source differs; refusing overwrite'
        return
    with (dest / 'kernel.asc').open('x') as out:
        out.write(source)


local = replace_once(base,
    '        mm.Init(&tiling, &pipe);\n        mm.SetOrgShape',
    '        mm.Init(&tiling, &pipe);\n        mm.SetOrgShape')
old = '''                // SetOrgShape retains full N for the strided output plane.
                mm.template IterateAll<true>(c[static_cast<uint64_t>(row) * tiling.N + col],
                                             k == 0U ? 0U : 1U);'''
new = '''                // A single base tile keeps CO1 allocated across Iterate calls.
                // Guard overflow until L0C wrap behavior is device-proven.
                const bool localAccum = tiling.Ka > SAFE_ACCUM_K &&
                    tiling.Ka < FIRST_POSSIBLE_INT32_OVERFLOW_K &&
                    tileM <= static_cast<uint32_t>(tiling.baseM) &&
                    tileN <= static_cast<uint32_t>(tiling.baseN);
                if (localAccum) {
                    mm.template Iterate<true>(k != 0U);
                    if (k + chunk == static_cast<uint32_t>(tiling.Ka)) {
                        mm.template GetTensorC<true>(
                            c[static_cast<uint64_t>(row) * tiling.N + col]);
                    }
                } else {
                    mm.template IterateAll<true>(
                        c[static_cast<uint64_t>(row) * tiling.N + col],
                        k == 0U ? 0U : 1U);
                }'''
local = replace_once(local, old, new)
emit('local-k', local)

# Safe full-K internal loop: no external SetTensor between partial sums.
internal = replace_once(base,
    '''                const uint32_t chunk = tiling.Ka - k < SAFE_ACCUM_K
                    ? tiling.Ka - k : SAFE_ACCUM_K;''',
    '''                const uint32_t chunk = tiling.Ka < FIRST_POSSIBLE_INT32_OVERFLOW_K
                    ? tiling.Ka - k : (tiling.Ka - k < SAFE_ACCUM_K
                    ? tiling.Ka - k : SAFE_ACCUM_K);''')
internal = replace_once(internal,
    'api.SetShape(std::min(M, tileM), std::min(N, tileN), std::min(K, SAFE_ACCUM_K));',
    '''api.SetShape(std::min(M, tileM), std::min(N, tileN),
        K < FIRST_POSSIBLE_INT32_OVERFLOW_K ? K : std::min(K, SAFE_ACCUM_K));''')
emit('local-k-safe', internal)

scale = (ROOT / 'optimization/candidates/conditional-wide-row-b/kernel.asc').read_text()
start = scale.index('        // Every shard computes the same final max')
end = scale.index('\n    }\n#endif', start)
scale = scale[:start] + '''        // One reduction owner per row; compact aligned metadata broadcast.
        AscendC::GlobalTensor<float> broadcast;
        broadcast.SetGlobalBuffer(reinterpret_cast<__gm__ float *>(partialAddress) +
            static_cast<uint64_t>(tiling.M) * shardCount * FLOAT_ALIGN_ELEMENTS,
            static_cast<uint64_t>(tiling.M) * FLOAT_ALIGN_ELEMENTS);
        for (uint32_t row = firstRow; row < rowEnd; ++row) {
            if (shard != row % shardCount) continue;
            float maximum = 0.0f;
            for (uint32_t part = 0; part < shardCount; ++part) {
                auto value = mmQueue.AllocTensor<float>();
                AscendC::DataCopy(value, partial[
                    (static_cast<uint64_t>(row) * shardCount + part) *
                    FLOAT_ALIGN_ELEMENTS], FLOAT_ALIGN_ELEMENTS);
                mmQueue.EnQue(value);
                value = mmQueue.DeQue<float>();
                const float x = value.GetValue(0);
                maximum = x > maximum ? x : maximum;
                mmQueue.FreeTensor(value);
            }
            const float scale = maximum > 0.0f ? maximum / 127.0f : 1.0f;
            auto metadata = yScaleQueue.AllocTensor<float>();
            AscendC::Duplicate(metadata, scale, FLOAT_ALIGN_ELEMENTS);
            AscendC::PipeBarrier<PIPE_V>();
            const auto vs = ::GetTPipePtr()->FetchEventID(AscendC::HardEvent::V_S);
            AscendC::SetFlag<AscendC::HardEvent::V_S>(vs);
            AscendC::WaitFlag<AscendC::HardEvent::V_S>(vs);
            metadata.SetValue(1, maximum == 0.0f ? 1.0f : 0.0f);
            yScaleQueue.EnQue(metadata);
            metadata = yScaleQueue.DeQue<float>();
            AscendC::DataCopy(broadcast[static_cast<uint64_t>(row) *
                FLOAT_ALIGN_ELEMENTS], metadata, FLOAT_ALIGN_ELEMENTS);
            AscendC::DataCopyExtParams copy = {1, 4, 0, 0, 0};
            AscendC::DataCopyPad(yScaleGlobal[row], metadata, copy);
            yScaleQueue.FreeTensor(metadata);
        }
        // Idle participants also reach both collectives.
        AscendC::SyncAll<false>();
        for (uint32_t row = firstRow; row < rowEnd; ++row) {
            auto metadata = mmQueue.AllocTensor<float>();
            AscendC::DataCopy(metadata, broadcast[static_cast<uint64_t>(row) *
                FLOAT_ALIGN_ELEMENTS], FLOAT_ALIGN_ELEMENTS);
            mmQueue.EnQue(metadata);
            metadata = mmQueue.DeQue<float>();
            const float scale = metadata.GetValue(0);
            const bool zero = metadata.GetValue(1) != 0.0f;
            mmQueue.FreeTensor(metadata);
            const uint32_t begin = shard * tile;
            const uint32_t end = begin + tile < tiling.N ? begin + tile : tiling.N;
            QuantizeRow(row, x1ScaleGlobal.GetValue(row), scale, zero, begin, end);
        }''' + scale[end:]
scale = replace_once(scale, '        if (shardMode) AscendC::SyncAll<false>();',
    '        if (shardMode) { AscendC::SyncAll<false>(); AscendC::SyncAll<false>(); }')
scale = replace_once(scale, 'static_cast<uint64_t>(M) * vectorShards * 32ULL : matrixBytes;',
    'static_cast<uint64_t>(M) * (vectorShards + 1U) * 32ULL : matrixBytes;')
emit('scale-owner', scale)

# Rebase the separately compiled/official historical ring, not its old fallback.
ring = (ROOT / 'optimization/candidates/row-ring-pipeline/kernel.asc').read_text()
ring = replace_once(ring,
    'const uint32_t tileM = useRowRing ? 16U : std::min(64U, QuantMatmulReluQuant::AlignUpHost(M, 16U));',
    'const uint32_t tileM = std::min(16U, QuantMatmulReluQuant::AlignUpHost(M, 16U));')
# Gate on enough jobs for actual overlap, preserving baseline elsewhere.
ring = replace_once(ring, 'const bool useRowRing = M >= 64U && N <= 4096U;',
    'const bool useRowRing = M >= 1024U && N <= 4096U;')
emit('tile-fifo', ring)
print('Created local-k, scale-owner, tile-fifo (paired row-job granularity)')
