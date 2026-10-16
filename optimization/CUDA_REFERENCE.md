# CUDA/CUTLASS 思路映射

本目录没有可直接复用的 `.cu` 实现；CUDA 参考只能用于算法结构映射，不能
直接编译到 AscendC。可迁移的核心思想来自 CUDA GEMM epilogue / fused
quantization：

1. **Fuse epilogue**：GEMM 结果在寄存器/共享内存中直接完成 scale、ReLU、row
   max 和 quantize，避免写回完整 FP32/INT32 矩阵再重新读取。
2. **Two-pass row reduction**：第一 pass 只保留每行 max，第二 pass 使用 row
   scale；如果硬件支持 epilogue 内部暂存，应将两次 GM 往返改为片上 tile
   暂存，而不是当前的 GM workspace + UB reload。
3. **Vectorized conversion**：CUDA 通常用 warp shuffle/reduction 和向量化
   pack；对应 AscendC 应使用 Compare/Select、Cast、Pack/掩码 API，避免每个
   元素 `GetValue` / `SetValue` 的标量循环。
4. **Tiling by M/N/K**：不要固定只沿 M 分 Cube。对较大的 N，应让 Cube tile
   沿 N 分块并在同一个 row group 内做协同 reduction；否则每个输出元素都被
   逐行 scalar epilogue 限制。

## 当前根 kernel 的最大结构性瓶颈

`VectorStage::QuantizeRow` 仍包含：

```text
for each element:
  LocalTensor.GetValue
  FastExactQuantPrepared (integer division emulation / branches)
  LocalTensor.SetValue
```

这是 AIV 标量 pipe 的强瓶颈嫌疑，仍需通过消融实验确认其占比。
4096 tile、reciprocal hint 和缓存激活不能移除逐元素标量工作。

## 可行的大幅优化路线

### 路线 A：允许量化语义使用硬件 RNE（首选性能路线）

将 exact scalar correction 替换为：

```text
fp activation -> vector Muls(reciprocal) -> vector Cast(RNE, int32/int16)
              -> vector Min/Max -> vector Cast(int8) -> GM
```

这与 CUDA 的 fused epilogue 最接近，可能获得数量级收益，但必须确认评测
是否要求 NumPy FP32 除法的逐元素 bit-exact 结果；当前严格 golden 下不能
未经边界测试直接启用。

### 路线 B：保留 exact 结果，做 fast/common path

用向量 hint 先完成硬件 RNE/FLOOR 量化；仅对检测到可能处于半整数边界的
少量元素走 `FastExactQuantPrepared`。这需要：

* 检测到最近半整数边界的距离，例如 `abs(q - (floor(q) + 0.5))`；
  不能把“靠近整数”当作危险条件；
* 生成 mask；
* 只把 mask 元素压缩/回收给 scalar pipe；
* 其余元素直接使用 vector 结果。

这是值得优先验证的“严格正确 + 减少标量工作”方向，但需要证明倒数、
乘法及转换误差的保守上界；固定经验 epsilon 不足以保证正确性。极小值、
subnormal、非有限值或上界不成立时必须整 tile 回退。还需验证 AscendC 的
Compare/Select/bitmask API 和 mask 到 scalar 索引的代价。

### 路线 C：Cube/AIV fused epilogue

重写 Cube tiling，使每个 AIC/AIV pair 处理完整的 `(M_tile,N_tile)`，在
片上保留 activation tile 并完成 row max 与量化。这有减少流量的潜力，
但并非已证明最优；改动较大，需要处理 N 分片的 row-max 合并、同步和
workspace 生命周期。完整行无法驻留时，局部 tile max 不能直接用于最终量化。

当前建议先实现路线 B 的独立候选版本，保留 exact fallback；不要直接修改
`op/kernel.asc` 基线。

## 已阅读的 CUDA 源码和参考

* [vLLM scaled_quant.cu](https://github.com/vllm-project/vllm/blob/main/csrc/quantization/w8a8/int8/scaled_quant.cu)
  （本次读取的文件 blob：`e620c1818475cdb803b2e5c893ae4be443049ec3`）。
  `dynamic_scaled_int8_quant_kernel` 使用 16-byte 对齐向量读写、
  `cub::BlockReduce`、共享行 max 和 `cvt.rni.sat.s8.f32`。
  不包含我们当前的逐元素软件整数校正。
  **语义差异**：它写出 `absmax / 127`，实际用 `127 / absmax` 乘输入；
  这不保证等价于先将 scale 舍入到 FP32 再除以 scale。
  它使用 absmax，本算子先 ReLU 再取 max；不能无条件移植。
* [CUTLASS Epilogue Visitor Trees 讲解](https://research.colfax-intl.com/epilogue_visitor_tree/)
  可参考 GEMM epilogue 融合的结构；完整行动态归约仍受 tile 所有权和同步约束。

## 第二版快照与实测

`op/kernel_v2.asc` 是本次研究前根目录 `kernel.asc` 的逐字节副本。
SHA256：`3d0e63cd4a9ac3023474ac05800783ed49b4ee38a00270da4c72d029210b63ad`。
`op/kernel.asc` 未改动。根 kernel 本轮没有引入新的未验证算法。

`suite_01_10.log` 的 20 次执行全部 INT8 零错误、scale 差值为零。
以下为固定 seed 的单次测量，不能替代隐藏评测或重复测量：

| ID | prior cycles | v2 cycles |
|---|---:|---:|
| 1 | 24157 | 24148 |
| 2 | 31893 | 31884 |
| 3 | 70522 | 73094 |
| 4 | 103179 | 100614 |
| 5 | 27598 | 28448 |
| 6 | 42198 | 42195 |
| 7 | 453769 | 433160 |
| 8 | 232338 | 226320 |
| 9 | 469401 | 448785 |
| 10 | 281796 | 274066 |

## 推荐实验顺序

1. 独立编译一个**仅用于性能消融**的全向量量化候选，统计 cycles 和
   mismatch，以测出移除标量校正的潜在收益；不能把其随机通过当作严格正确。
2. 使用 Compare 输出的紧凑 bitmask，按 mask word 跳过安全元素，只对
   有风险的 bit 调用原 exact helper；不要仍逐元素读取激活检查距离。
3. 建立保守误差证书及半整数两侧/subnormal 回归，再启用严格 fast path。
4. 若该阶段提速后 Cube 或 workspace 流量成为主要成本，再推进融合、
   双缓冲和 M/N 二维 tiling。当前小 M 的 core ownership 不能仅改分块常数。

没有实测和误差证明前，不承诺数量级加速或保留严格正确性。
