"""Run one isolated v3 candidate with the existing strict leased harness."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
name = sys.argv[1]
assert name in ('dual-aiv-corrected', 'fifo-ub8192')
source = (HERE.parent / 'structural-breakthrough-v2/checks.py').read_text()
source = source.replace("HERE = Path(__file__).resolve().parent", "HERE = Path(__file__).resolve().parent")
source = source.replace("for name in ('dual-aiv', 'ub-resident-8192'):", f"for name in ({name!r},):")
source = source.replace("('ub-resident-8192', ((2, 4097, 33), (2, 8192, 33), (2, 8201, 33))),",
    "('dual-aiv-corrected', ((17, 513, 65), (65, 257, 33)))," if name == 'dual-aiv-corrected' else
    "('fifo-ub8192', ((1025, 65, 33), (2, 4097, 33), (2, 8201, 33))),")
sys.argv = [str(Path(__file__)), '--smoke']
exec(compile(source, str(Path(__file__)), 'exec'))
