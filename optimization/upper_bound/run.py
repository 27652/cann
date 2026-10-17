#!/usr/bin/env python3
import argparse, hashlib, json, os, re, subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parents[1]))
from int32_golden import reference
from camodel_resource import lease

HERE = Path(__file__).resolve().parent
BIN = HERE / "build/bench_upper_bound"
OUT = HERE / "results"

def one(shape, mode, tag, seed, timeout=600):
    m,n,k = shape
    d = OUT / tag / str(mode)
    inp = d / "input"; out = d / "output"; logs = d / "logs"
    inp.mkdir(parents=True, exist_ok=False); out.mkdir(exist_ok=False); logs.mkdir(exist_ok=False)
    rng=np.random.default_rng(seed)
    a=rng.integers(-128,128,(m,k),dtype=np.int8); b=rng.integers(-128,128,(n,k),dtype=np.int8)
    s=rng.uniform(.001,.1,m).astype(np.float32); t=rng.uniform(.001,.1,n).astype(np.float32)
    for name,v in zip(("x1","x2","x1Scale","x2Scale"),(a,b,s,t)): v.tofile(inp/(name+".bin"))
    ey,es,_=reference(a,b,s,t); ey.tofile(out/"golden_y.bin"); es.tofile(out/"golden_yScale.bin")
    env=dict(os.environ, CAMODEL_LOG_PATH=str(logs), STARS_LOG_PATH=str(logs), OPENBLAS_NUM_THREADS="1")
    fingerprint = {"binary_sha256": hashlib.sha256(BIN.read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256(b''.join(v.tobytes() for v in (a,b,s,t))).hexdigest(),
        "golden_sha256": hashlib.sha256(ey.tobytes()+es.tobytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "environment": {key: value for key,value in sorted(os.environ.items())
            if key.startswith(('ASCEND_', 'CAMODEL_', 'CANN_', 'LD_LIBRARY_PATH'))},
        "source_identity": json.loads((HERE/'source-identity.json').read_text())}
    (d/'fingerprint.json').write_text(json.dumps(fingerprint,indent=2)+'\n')
    try:
        with lease() as fd:
            env['CAMODEL_LEASE_FD'] = str(fd)
            p=subprocess.run([str(BIN),str(m),str(n),str(k),str(mode)],cwd=d,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout,pass_fds=(fd,))
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or b''
        (d/'run.log').write_text(output.decode(errors='replace') if isinstance(output,bytes) else output)
        r = dict(shape=shape,mode=mode,status='timeout',timeout_seconds=timeout,fingerprint=fingerprint)
        (d/'failure.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps(r),flush=True)
        raise
    except RuntimeError as exc:
        r = dict(shape=shape, mode=mode, status='blocked', reason=str(exc),
                 fingerprint=fingerprint)
        (d/'failure.json').write_text(json.dumps(r,indent=2)+'\n')
        print(json.dumps(r),flush=True)
        raise
    (d/"run.log").write_text(p.stdout)
    r={"shape":shape,"mode":mode,"tag":tag,"seed":seed,"fingerprint":fingerprint,"binary_sha256":fingerprint['binary_sha256'],"returncode":p.returncode}
    if p.returncode==0 and (d/"output/y.bin").exists():
        y=np.fromfile(d/"output/y.bin",np.int8).reshape(m,n); ys=np.fromfile(d/"output/yScale.bin",np.float32)
        r.update(int8_mismatches=int(np.count_nonzero(y!=ey)),scale_max_diff=float(np.max(np.abs(ys-es))),
                 scale_ok=bool(np.allclose(ys,es,rtol=1e-4,atol=1e-4)))
    task=logs/"profile_task_log0.toml"
    if task.exists():
        q=re.search(r"^\s*duration\s*=\s*(\d+)",task.read_text(),re.M)
        if q:r["task_cycles"]=int(q.group(1))
    (d/"result.json").write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r),flush=True)
    if p.returncode: raise RuntimeError(f'benchmark exit {p.returncode}: {d}')

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument('--shape',default='2x1025x32')
    parser.add_argument('--modes',nargs='+',type=int,choices=range(5),default=[0,2,3,4])
    parser.add_argument('--tag',required=True)
    parser.add_argument('--timeout',type=int,default=600)
    args=parser.parse_args()
    shape=tuple(map(int,args.shape.split('x')))
    if len(shape)!=3 or min(shape)<=0: parser.error('expected positive MxNxK')
    if 4 in args.modes and not (shape[0]<=32 and shape[1]>=1024 and shape[2]<65536):
        parser.error('N split restricted to M<=32, N>=1024, K<65536')
    for mode in args.modes: one(shape,mode,args.tag,20261017,args.timeout)
