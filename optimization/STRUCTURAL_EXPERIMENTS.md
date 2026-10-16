# 四方向实验进度

本轮修改根目录 `kernel.asc`，已冻结为 `op/kernel_v3.asc`。
`op/kernel.asc` 和 `op/kernel_v2.asc` 保持不变。
默认开启的 mask 路径仍是实验候选，不能据随机回归宣称对所有输入严格正确。
可编译 `QUANT_MASK_FAST_PATH=0` 关闭；`bench_v2` 是此前独立冻结版本。

## 1. 全向量量化消融

`bench_vector` 定义 `QUANT_VECTOR_ONLY=1`、`QUANT_MASK_FAST_PATH=0`。
用硬件 RNE 替代所有逐元素整数校正。用来量化标量成本，不作为严格版本。
极小 scale 的 Div 路径仍可能受硬件精度影响。

## 2. 边界 mask + exact fallback

根 kernel 对 N>16 且 outputScale 在 [1e-20,1e20] 内启用：

1. 保留 approximate quotient；vector floor 得到整数。
2. vector 构造 `abs(q - (floor(q)+0.5))`。
3. Compare 生成紧凑 bitmask，距离 <= 1/1024 时置位。
4. vector RNE 生成所有输出；scalar 每 32 lane 读一次 mask，仅修正置位元素。
5. 非安全 scale 区间和小 N 继续全元素 exact 校正。

### 正确性边界

若 scalar reciprocal 与 vector multiply 符合正确舍入 FP32，真实 quotient
至多约 128，则 1/1024 明显大于 reciprocal/multiply 和 FP32 division
舍入的组合绝对误差；远离半整数的 RNE 结果保持不变。
但这不是设备 ISA 误差界证明：仍须确认 scalar reciprocal 的实际 lowering、
向量乘法的精度/flush 行为与 mask layout。当前宿主检查以 IEEE 模型为前提。
该 guard 没有验证所有输入是否 finite，沿用原 helper 的 finite-input 契约。

`check_quant.py` 新增 200 万次混合随机与半整数邻域测试，1001783 次 fallback。
设备边界测试 `--mode half_boundary --shapes 2x1144x32` 构造 dot=1，
rowMax=127、scale=1，每个半整数两侧 +/-4 ULP，保存到 `boundary_device.log`。
这仍不是所有 scale 的设备精度证明。

设备边界测试已完成：v2 / mask / vector-only 均为零 INT8 错误、scale 差值零。
cycles 分别为 384334 / 319888 / 33034。该构造的 scale=1，使倒数精确，
因此它检验半整数 RNE 与 fallback，但不能检验非精确倒数导致的边界偏移。
边界密集时 mask 需要大量 scalar fallback，收益下降到约 1.20 倍。

### 首轮单次 CAModel（同固定 seed）

| M,N,K | v2 cycles | mask cycles | vector-only cycles |
|---|---:|---:|---:|
| 16,16,32 | 73094 | 74809 | 43047 |
| 17,33,65 | 100614 | 54220 | 45648 |
| 16,256,256 | 433160 | 60356 | 46622 |
| 2,1025,32 | 226320 | 39053 | 32183 |
| 32,65,257 | 274066 | 91137 | 74832 |

上述五点 mask/vector 均 INT8 零错误、scale 差值为零。
v2 来自 `suite_01_10.log`，新版本来自 `suite_mask.log`。
这些是 task cycles，不是实体设备微秒；编译代码布局变化也会影响小尺寸。

## 3. 片上 activation 缓存 / epilogue 融合

`bench_cache` 定义 `QUANT_CACHE_TWO_TILES=1`：
对于 4096<N<=8192 的两 tile 行，第一遍额外保留首 tile 的 activation，
第二遍恢复它以避免首 tile 的 GM load、scale 和 ReLU；末 tile 正常重读。
增加 16KB UB，不能无限扩大缓存。比较命令：

```bash
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py \
  --shapes 2x4097x32 --variants optimized cache tile128
```

这只是减少一次 GM 重读，不是 Cube epilogue 融合。
完整融合需要改变 Matmul 输出目的地和客户端协议；不能以局部 max 代替全行 max。

上述缓存对照已完成：optimized=75111、cache=74272 cycles，单次快 1.12%。
全部 INT8 零错误、scale 差值零。额外 16KB UB 暂不默认开启，需更多 shape
及重复测量确认收益，而不是将它当作主要优化。

## 4. M/N 二维分块及流水

`bench_tile128` 定义 `QUANT_BASE_N=128U`，测试 Cube 内部 N tile 粒度；
保留每 core 完整 N 的 ownership，不需要新全局归约。
这不是跨核二维分块，也不是双缓冲流水实现。

同一个 2x4097x32 随机输入上 tile128=98552 cycles，比默认 75111 慢 31.21%。
输出正确，但该点不支持采用 N tile=128，保持默认 256。

完整跨核二维分块需要 partial row-max workspace、跨核同步以及第二阶段
量化调度；当前 KFC 路径不具备该协议。此前直接改变行分区曾产生全错，
因此本轮没有把未验证的 ownership 改动混入根 kernel。
只有在量化提速后测出 Cube 为主要成本时，才值得继续该大规模重写。

## 文件与回归

* `suite_mask.log`：首轮随机/极值消融。
* `suite_edge_mask.log`：zero/negative/tiny scale 回归。
  ID 1/5/6/9/10 的 prior、mask、vector 共 15 次均通过；ID 15 的 prior
  曾超过 240 秒超时，导致后续两个版本未执行，不属于输出校验失败。
  后续使用 `--case-ids 15 --variants optimized vector prior --timeout 1800`
  完成补测：三个版本均 `mismatches=0`、`scale_ok=true`、`scale_max_diff=0.0`。
  ID 15 的 task cycles 为 optimized=608553、vector=64844、prior=1452970。
* `boundary_device.log`：半整数设备仿真。
* `cache_tile.log`：缓存和内部 N tile 实验。

尚在执行的测试不视为已通过。不能把 vector-only 的随机通过视为精确性保证。
