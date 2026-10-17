#!/usr/bin/env python3
"""Host-only tests; deliberately does NOT emit strict/device-pass fields."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
source = (ROOT / "kernel.asc").read_text()
compact = source[source.index("__aicore__ inline uint32_t CompactLowestLane"):source.index("// Experimental variants")]
# The source slice includes the AscendC include because the prototype helper
# was inserted before it; host compilation needs only the helper body.
compact = compact[:compact.index('\n#include "kernel_operator.h"')]
helpers = source[source.index("__aicore__ inline uint32_t FastExactQuantPrepared"):source.index("namespace QuantMatmulReluQuant")]
test = r'''
#include <cstdint>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <initializer_list>
''' + compact.replace("__aicore__", "") + helpers.replace("__aicore__", "") + r'''
uint32_t state=20261017;
uint32_t rng(){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
float frombits(uint32_t u){float f;std::memcpy(&f,&u,4);return f;}
int main(){
    uint64_t masks=0, lanes=0, exact=0, vectorFailures=0;
    // The scalar index map is tested independently of unproven device mask layout.
    for(uint32_t valid=1;valid<=4096;++valid){
        for(uint32_t base=0;base<valid;base+=32){
            uint32_t original=rng(),bits=original, previous=0, count=0;
            uint16_t indices[32];
            while(bits){uint32_t lane=CompactLowestLane(bits);
                if(lane>=32 || !(original&(1U<<lane))) return 1;
                if(count && lane<=previous) return 2;
                previous=lane;
                if(base+lane<valid) indices[count++]=static_cast<uint16_t>(base+lane);
                bits&=bits-1U;
            }
            uint32_t expected=0;
            for(uint32_t lane=0;lane<32;++lane) if(base+lane<valid && (original&(1U<<lane))){
                if(indices[expected++]!=base+lane) return 3;
            }
            if(count!=expected) return 4;
            ++masks; lanes+=count;
        }
    }
    // All singleton bits and dense words, including terminal lane 4095.
    for(uint32_t lane=0;lane<32;++lane) if(CompactLowestLane(1U<<lane)!=lane) return 5;
    for(uint32_t bits: {0xffffffffU,0x80000001U,0xaaaaaaaaU,0x55555555U}){
        uint32_t b=bits; while(b){uint32_t i=CompactLowestLane(b); if((b&(~b+1U))!=(1U<<i))return 6;b&=b-1U;}
    }
    for(uint32_t j=0;j<200000;++j){
        uint32_t a=rng()&0x7fffffffU,b=rng()&0x7fffffffU;
        if(!b || a>=0x7f800000U || b>=0x7f800000U) continue;
        for(uint32_t hint: {0U,127U,rng()}){
            if(FastExactQuantBits(a,b,hint)!=ExactQuantBits(a,b))return 7;
            ++exact;
        }
    }
    // Show why A cannot be strict: even host IEEE reciprocal multiplication
    // differs from RN32 division at some half-integer boundaries.
    for(uint32_t j=0;j<500000;++j){
        float b=1.0f+float(rng()&0xffffffU)/16777216.0f;
        float center=(float(rng()%127)+0.5f)*b;
        uint32_t bits;std::memcpy(&bits,&center,4);
        float a=frombits(bits+int(rng()%5)-2);
        volatile float inv=1.0f/b;
        volatile float q=a*inv;
        uint32_t result=static_cast<uint32_t>(std::nearbyint(q));
        if(result>127)result=127;
        if(result!=ExactQuant(a,b)){
            if(!vectorFailures) std::printf("A_COUNTEREXAMPLE a=%a b=%a q=%a actual=%u expected=%u\n",a,b,float(q),result,ExactQuant(a,b));
            ++vectorFailures;
        }
    }
    if(!vectorFailures) return 8;
    std::printf("HOST_ONLY masks=%llu staged_lanes=%llu exact_checks=%llu A_counterexamples=%llu\n",
        (unsigned long long)masks,(unsigned long long)lanes,(unsigned long long)exact,(unsigned long long)vectorFailures);
}
'''
cpp = ROOT / "build" / "host_checks.cpp"
binary = ROOT / "build" / "host_checks"
cpp.write_text(test)
subprocess.run(["g++", "-O2", "-std=c++17", "-ffp-contract=off", str(cpp), "-o", str(binary)], check=True)
result = subprocess.run([str(binary)], capture_output=True, text=True)
print(result.stdout, end="")
print(result.stderr, end="")
(ROOT / "host_checks.json").write_text(json.dumps({
    "evidence_type": "host_only_not_device_validation",
    "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
    "returncode": result.returncode, "stdout": result.stdout,
    "device_validation_completed": False,
    "fast_track_eligible": {"A": False, "B": False},
}, indent=2) + "\n")
raise SystemExit(result.returncode)
