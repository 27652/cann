#!/usr/bin/env python3
"""Host-side proof regression for arbitrary and reciprocal-derived hints."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
source = (root.parent / "kernel.asc").read_text()
helpers = source[source.index("__aicore__ inline uint32_t FastExactQuantPrepared"):source.index("namespace QuantMatmulReluQuant")]
helpers = helpers.replace("__aicore__", "")
test = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cmath>
'''+ helpers + r'''
uint32_t state = 20261016;
uint32_t random32() { state ^= state << 13; state ^= state >> 17; state ^= state << 5; return state; }
float asfloat(uint32_t u) { float f; std::memcpy(&f, &u, 4); return f; }
int main() {
    unsigned long long count = 0;
    for (unsigned j=0; j<1000000; ++j) {
        uint32_t a = random32() & 0x7fffffffU;
        uint32_t b = random32() & 0x7fffffffU;
        if (!b || a >= 0x7f800000U || b >= 0x7f800000U) continue;
        uint32_t reference = ExactQuantBits(a,b);
        for (uint32_t hint : {0U, 127U, random32()}) {
            if (FastExactQuantBits(a,b,hint) != reference) {
                std::printf("FAIL a=%08x b=%08x hint=%u\n",a,b,hint); return 1;
            }
            ++count;
        }
        float x=asfloat(a), y=asfloat(b);
        float hint = y > 1e-30f ? x * (1.0f/y) : x/y;
        if (FastExactQuant(x,y,hint) != reference) return 2;
        ++count;
    }
    // Exercise both sides of all representable half-integer thresholds.
    for (unsigned n=0; n<127; ++n) {
        const float half = float(n)+0.5f;
        for (float scale : {1.0f, 0.003f, 1e-35f, 1e-20f, 1e20f}) {
            float center = half * scale;
            uint32_t bits; std::memcpy(&bits, &center, 4);
            for (int delta=-8; delta<=8; ++delta) {
                float x=asfloat(bits+delta);
                volatile float quotient=x/scale;
                uint32_t expected=static_cast<uint32_t>(std::nearbyint(quotient));
                if (expected>127) expected=127;
                float hint=scale>1e-30f ? x*(1.0f/scale) : x/scale;
                if (FastExactQuant(x,scale,hint)!=expected) return 3;
                ++count;
            }
        }
    }
    std::printf("PASS: %llu exact-quantization checks\n",count);
    unsigned long long masked=0, fallback=0;
    // Host IEEE model of the mask certificate. Device reciprocal accuracy and
    // Compare bit layout must also be checked by CAModel boundary cases.
    for (unsigned j=0; j<2000000; ++j) {
        float scale=std::exp2(float(int(random32()%133)-66)) *
            (1.0f+float(random32()&65535)/65536.0f);
        float center=(j&1U) ? (float(random32()%127)+0.5f)*scale :
            (float(random32()%128000)/1000.0f)*scale;
        uint32_t bits; std::memcpy(&bits,&center,4);
        int delta = static_cast<int>(random32()%65U) - 32;
        float x=asfloat(bits+static_cast<uint32_t>(delta));
        volatile float inv=1.0f/scale;
        volatile float q=x*inv;
        bool risk=std::fabs(q-(std::floor(q)+0.5f))<=0.0009765625f;
        uint32_t actual=risk ? FastExactQuant(x,scale,q) :
            static_cast<uint32_t>(std::nearbyint(q));
        if (actual>127) actual=127;
        if (actual!=ExactQuant(x,scale)) return 4;
        ++masked; fallback+=risk;
    }
    std::printf("PASS: %llu mask-boundary checks, %llu fallbacks\n",masked,fallback);
}
'''
test = '#include <initializer_list>\n' + test
with tempfile.TemporaryDirectory(prefix="quant_check_", dir="/tmp/opencode") as tmp:
    cpp = Path(tmp) / "check.cpp"
    exe = Path(tmp) / "check"
    cpp.write_text(test)
    subprocess.run(["g++", "-O2", "-std=c++17", "-ffp-contract=off", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
