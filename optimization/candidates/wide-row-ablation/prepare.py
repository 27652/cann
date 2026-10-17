"""Create isolated ablations from immutable formal sources; never edit parents."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/tile16-persistent-6ad31941/source/kernel.asc'
FULL = ROOT / 'evidence/formal/wide-row-tile-cv-6ad32394/source/kernel.asc'


def section(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]


def generate():
    base, full = BASE.read_text(), FULL.read_text()
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == 'cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae'
    assert hashlib.sha256(FULL.read_bytes()).hexdigest() == 'a10a49eade1023836c32193cd6f0f70da251b3a53d941cac385bea50c26d8af8'
    # Cube body and host tiling/block count are identical, not two independent factors.
    assert section(base, '    // Every AIC owns', '    // Fusion SyncAll') == section(full, '    // Every AIC owns', '    // Fusion SyncAll')
    assert section(base, 'inline bool GenerateTileTiling', '} // namespace') == section(full, 'inline bool GenerateTileTiling', '} // namespace')
    assert section(base, '    const uint32_t tileM =', '    uint8_t *scratch') == section(full, '    const uint32_t tileM =', '    uint8_t *scratch')
    # Restore baseline mask eligibility and baseline whole-row mapping outside shardMode.
    mask_start = '        const bool useBoundaryMask ='
    mask_end = '        // A row has one denominator.'
    vector_only = full.replace(section(full, mask_start, mask_end), section(base, mask_start, mask_end))
    old_rows = '''        const uint32_t rowsPerBlock = (tiling.M + blocks - 1U) / blocks;
        const uint32_t first = shard ? 0U : block * rowsPerBlock;
        const uint32_t end = shard ? tiling.M :
            (first + rowsPerBlock < tiling.M ? first + rowsPerBlock : tiling.M);'''
    new_rows = '''        const uint32_t first = shard ? 0U :
            static_cast<uint64_t>(tiling.M) * block / blocks;
        const uint32_t end = shard ? tiling.M :
            static_cast<uint64_t>(tiling.M) * (block + 1U) / blocks;'''
    assert old_rows in vector_only
    vector_only = vector_only.replace(old_rows, new_rows)
    # Empty shards must publish zero maxima and participate in barriers, but never quantize.
    ancillary = full.replace('#define EXPERIMENT_N_SHARD 1', '#define EXPERIMENT_N_SHARD 0')
    # Preserve candidate ceil-row assignment without sharding, to isolate all ancillary changes.
    floor_rows = '''        const uint32_t first = static_cast<uint64_t>(tiling.M) * block / blocks;
        const uint32_t end = static_cast<uint64_t>(tiling.M) * (block + 1U) / blocks;'''
    ceil_rows = '''        const uint32_t rowsPerBlock = (tiling.M + blocks - 1U) / blocks;
        const uint32_t first = block * rowsPerBlock;
        const uint32_t end = first + rowsPerBlock < tiling.M ? first + rowsPerBlock : tiling.M;'''
    assert floor_rows in ancillary
    ancillary = ancillary.replace(floor_rows, ceil_rows)
    return {'baseline': base, 'vector-only': vector_only, 'ancillary-only': ancillary}


if __name__ == '__main__':
    hashes = {}
    for name, source in generate().items():
        dest = HERE / name
        dest.mkdir(exist_ok=False)
        (dest / 'kernel.asc').write_text(source)
        hashes[name] = hashlib.sha256(source.encode()).hexdigest()
    (HERE / 'source-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(json.dumps(hashes, indent=2))
