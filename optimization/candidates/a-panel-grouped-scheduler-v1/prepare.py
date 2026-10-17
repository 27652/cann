"""Freeze an independent grouped tile scheduler; never overwrite a project."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'evidence/formal/tile16-persistent-6ad31941/source'
source = (BASE / 'kernel.asc').read_text()
assert hashlib.sha256(source.encode()).hexdigest() == (
    'cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae')
old = '''        for (uint64_t task = block; task < taskCount; task += blocks) {
            const uint32_t row = (task % mTiles) * tileM;
            const uint32_t col = (task / mTiles) * tileN;'''
new = '''        // Consecutive N tiles of an A row panel remain on one AIC.
        // This changes scheduling/locality only, not Matmul's L1 lifetime.
        constexpr uint32_t panelTiles = 4U;
        const uint32_t nGroups = (nTiles + panelTiles - 1U) / panelTiles;
        const uint64_t groupCount = static_cast<uint64_t>(mTiles) * nGroups;
        // Avoid sacrificing parallelism when there are too few panel groups.
        const bool grouped = groupCount >= blocks && nTiles > 1U;
        const uint64_t workCount = grouped ? groupCount : taskCount;
        for (uint64_t work = block; work < workCount; work += blocks) {
            const uint32_t mIndex = grouped ? work % mTiles : work % mTiles;
            const uint32_t firstN = grouped ? (work / mTiles) * panelTiles : work / mTiles;
            const uint32_t endN = grouped ?
                (firstN + panelTiles < nTiles ? firstN + panelTiles : nTiles) : firstN + 1U;
            for (uint32_t nIndex = firstN; nIndex < endN; ++nIndex) {
            const uint32_t row = mIndex * tileM;
            const uint32_t col = nIndex * tileN;'''
assert source.count(old) == 1
source = source.replace(old, new)
end = '''                k += chunk;
            }
        }
        mm.End();'''
assert source.count(end) == 1
source = source.replace(end, '''                k += chunk;
            }
            }
        }
        mm.End();''')
project = HERE / 'submit-project'
assert not project.exists(), 'Refusing to overwrite existing candidate'
shutil.copytree(BASE, project)
(project / 'kernel.asc').write_text(source)
hashes = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in project.rglob('*') if p.is_file()}
(HERE / 'project-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
print(json.dumps(hashes, indent=2))
