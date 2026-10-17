"""Isolated N-tile max pipeline; never overwrite frozen parent or root."""
from pathlib import Path
import hashlib
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
s = (ROOT/'evidence/formal/tile-fifo-6ad335a8/source/kernel.asc').read_text()
assert hashlib.sha256(s.encode()).hexdigest() == '427a35b31dbc75c3afbb8b1681c68f6c852b8f3b5620ca889c62c56f6083bef4'

def edit(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)

edit('    __aicore__ inline void ProcessRows(uint32_t firstRow, uint32_t rowEnd)', '''    __aicore__ inline void AccumulateTileMax(uint32_t first, uint32_t end,
        uint32_t column, uint32_t count, float *maxima)
    {
        for (uint32_t row = first; row < end; ++row) {
            LoadAndActivate(row, column, count, AlignUpDevice(count, FLOAT_ALIGN_ELEMENTS),
                            x1ScaleGlobal.GetValue(row));
            auto out = reduceOutBuffer.Get<float>();
            AscendC::ReduceMax(out, fpBuffer.Get<float>(), reduceWorkBuffer.Get<float>(),
                static_cast<int32_t>(AlignUpDevice(count, FLOAT_ALIGN_ELEMENTS)), false);
            AscendC::PipeBarrier<PIPE_V>();
            const float x = out.GetValue(0);
            maxima[row-first] = x > maxima[row-first] ? x : maxima[row-first];
        }
    }

    __aicore__ inline void FinishKnownMax(uint32_t row, float maximum)
    {
        const float scale = maximum > 0.0f ? maximum / 127.0f : 1.0f;
        auto out = yScaleQueue.AllocTensor<float>();
        AscendC::Duplicate(out, scale, FLOAT_ALIGN_ELEMENTS);
        yScaleQueue.EnQue(out);
        out = yScaleQueue.DeQue<float>();
        AscendC::DataCopyExtParams copy = {1, 4, 0, 0, 0};
        AscendC::DataCopyPad(yScaleGlobal[row], out, copy);
        yScaleQueue.FreeTensor(out);
        QuantizeRow(row, x1ScaleGlobal.GetValue(row), scale, maximum == 0.0f);
    }

    __aicore__ inline void ProcessRows(uint32_t firstRow, uint32_t rowEnd)''')
# Extend the existing ring only on a new wide-N dispatch. Narrow path untouched.
edit('    const uint32_t jobs = (tiling.M + rowTile - 1U) / rowTile;',
'''    const bool tilePipeline = tiling.N > VECTOR_TILE_N;
    const uint32_t jobs = (tiling.M + rowTile - 1U) / rowTile;''')
edit('                column += tileN;','''                if (tilePipeline) {
                    AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(4U);
                    AscendC::CrossCoreWaitFlag(6U);
                }
                column += tileN;''')
edit('            AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(4U + slot);',
'''            AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(tilePipeline ? 5U : 4U + slot);''')
edit('            if (i >= 2U) AscendC::CrossCoreWaitFlag(6U + slot);',
'''            if (tilePipeline && i > 0U) AscendC::CrossCoreWaitFlag(7U);
            if (!tilePipeline && i >= 2U) AscendC::CrossCoreWaitFlag(6U + slot);''')
edit('''        for (uint32_t i = localJobs > 2U ? localJobs - 2U : 0U; i < localJobs; ++i)
            AscendC::CrossCoreWaitFlag(6U + i % 2U);''','''        if (tilePipeline) {
            if (localJobs) AscendC::CrossCoreWaitFlag(7U);
        } else {
            for (uint32_t i = localJobs > 2U ? localJobs - 2U : 0U; i < localJobs; ++i)
                AscendC::CrossCoreWaitFlag(6U + i % 2U);
        }''')
edit('            AscendC::CrossCoreWaitFlag(4U + slot);',
'''            if (!tilePipeline) AscendC::CrossCoreWaitFlag(4U + slot);''')
edit('            stage.ProcessRows(first, end);','''            if (tilePipeline) {
                float maxima[16] = {};
                for (uint32_t column = 0; column < static_cast<uint32_t>(tiling.N);) {
                    const uint32_t count = tiling.N - column < tiling.singleCoreN
                        ? tiling.N - column : tiling.singleCoreN;
                    AscendC::CrossCoreWaitFlag(4U);
                    stage.AccumulateTileMax(first, end, column, count, maxima);
                    AscendC::PipeBarrier<PIPE_ALL>();
                    AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(6U);
                    column += count;
                }
                AscendC::CrossCoreWaitFlag(5U);
                for (uint32_t row = first; row < end; ++row)
                    stage.FinishKnownMax(row, maxima[row-first]);
            } else {
                stage.ProcessRows(first, end);
            }''')
edit('            AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(6U + slot);',
'''            AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(tilePipeline ? 7U : 6U + slot);''')
edit('const bool useRowRing = M >= 1024U && N <= 4096U;',
     'const bool useRowRing = M >= 1024U && N <= 16384U;')
edit('            if (tilePipeline && i > 0U) AscendC::CrossCoreWaitFlag(7U);',
     '            if (tilePipeline && i > 0U) AscendC::CrossCoreWaitFlag(9U);')
edit('''            for (uint32_t column = 0; column < static_cast<uint32_t>(tiling.N);) {
                const uint32_t tileN''',
'''            for (uint32_t column = 0; column < static_cast<uint32_t>(tiling.N);) {
                const uint32_t tileIndex = column / tiling.singleCoreN;
                if (tilePipeline && tileIndex >= 2U)
                    AscendC::CrossCoreWaitFlag(6U + tileIndex % 2U);
                const uint32_t tileN''')
edit('''                    AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(4U);
                    AscendC::CrossCoreWaitFlag(6U);''',
'''                    AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(4U + tileIndex % 2U);''')
edit('''            AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(tilePipeline ? 5U : 4U + slot);''',
'''            if (tilePipeline) {
                const uint32_t tiles = (tiling.N + tiling.singleCoreN - 1U) / tiling.singleCoreN;
                for (uint32_t t = tiles > 2U ? tiles - 2U : 0U; t < tiles; ++t)
                    AscendC::CrossCoreWaitFlag(6U + t % 2U);
            }
            AscendC::CrossCoreSetFlag<0x2, PIPE_FIX>(tilePipeline ? 8U : 4U + slot);''')
edit('            if (localJobs) AscendC::CrossCoreWaitFlag(7U);',
     '            if (localJobs) AscendC::CrossCoreWaitFlag(9U);')
edit('                    AscendC::CrossCoreWaitFlag(4U);',
'''                    const uint32_t tileIndex = column / tiling.singleCoreN;
                    AscendC::CrossCoreWaitFlag(4U + tileIndex % 2U);''')
edit('                    AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(6U);',
     '                    AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(6U + tileIndex % 2U);')
edit('                AscendC::CrossCoreWaitFlag(5U);',
     '                AscendC::CrossCoreWaitFlag(8U);')
edit('            AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(tilePipeline ? 7U : 6U + slot);',
     '            AscendC::CrossCoreSetFlag<0x2, PIPE_MTE2>(tilePipeline ? 9U : 6U + slot);')
edit('    const bool useRowRing = M >= 1024U && N <= 16384U;',
'''#ifndef N_TILE_MIN_ROWS
#define N_TILE_MIN_ROWS 1024U
#endif
    const bool useRowRing = M >= N_TILE_MIN_ROWS && N <= 16384U;''')
dest=HERE/'kernel.asc'
if dest.exists():
    assert dest.read_text()==s
else:
    dest.write_text(s)
print(hashlib.sha256(s.encode()).hexdigest())
