# 参考资料到当前 kernel 的映射分析

## 分析框架

本项目的优化目标是：在满足题目正确性要求的前提下，改善正式题目计时口径下
的用时。下面的顺序是当前工程的分析建议，不是第三方资料给出的结论：

1. 是否减少端到端 GM 往返和同步；
2. 是否减少 row max/quant 的标量控制与 `GetValue/SetValue`；
3. 是否改善 Cube 利用率和多核负载均衡；
4. 是否保持题目的 FP32、ReLU、rint、clamp 和 zero-row 语义。

## A. 瓶颈假设：精确量化与标量控制

历史 vector-only 消融显示明显 cycle 差异（见
`../optimization/STRUCTURAL_EXPERIMENTS.md`），支持进一步研究精确校正成本。
但该消融改变了指令和同步，且不保证数值等价；不能直接当作当前全部 shape 的
分阶段耗时比例，也不是可达到的性能上界/下界证明。

当前 `kernel.asc::QuantizeRow` 的主要路径是：

```text
FP32 activation tile
  → reciprocal/Div + vector hint
  → 可选 boundary Compare
  → V_S 同步
  → scalar GetValue / exact integer correction / SetValue
  → Cast / DataCopy
```

可研究向量化归约和稀疏精确校正。以下是本工程的未实现候选，不是已确认存在于
vLLM 或官方 DynamicQuant 中的 exact-correction 算法：

- 第一阶段向量计算 quotient、floor hint 和风险 mask；
- 预先生成原始 lane 索引；适配 mask 后，分别用 GatherMask 筛选值和索引；
- 只对压缩后的风险 lane 执行 exact correction；
- 用 index 恢复原列位置，再 Select/Scatter 写回；
- 只有在风险判据可靠的前提下，未命中的 lane 才能直接保留向量 RNE 结果。

风险判据需要覆盖近似商与参考 FP32 除法可能产生不同整数舍入的全部情况；仅验证
mask 位序和几个测试点不足以证明它成立。当前误差界有设备精度前提，见
`../ev/QUANT_ERROR_BOUND.md`。CreateVecIndex 生成索引，不自动执行反向映射。

是否采用这条路径，至少需要验证风险 mask 位序、GatherMask 输出布局、索引恢复、
尾块和 int8 Cast，并比较其额外指令、同步和数据搬运成本。若这些条件尚未确认，
当前全元素 exact 路径仍是可回退的基线。`Select` 按条件选择值，不压缩 lane；
是否减少后续工作量取决于完整算法，而不是调用 Select 本身。

## B. Cube/Vector 融合

GroupedMatmulQuantMixCore 和 FFNQuant 暗示当前可以重点比较两种结构：

### 方案 B1：保持当前 ownership，缩短 workspace 生命周期

- Cube 写一个可被 Vector 立即消费的 tile；
- AIC/AIV 以 tile 为单位 `CrossCoreSetFlag/WaitFlag`；
- Vector 完成 dequant/ReLU/row-max 中间统计后复用 UB；
- 只有需要第二遍量化的结果才写 workspace/GM。

这种方案可能减少中间结果往返；动态 row max 仍可能需要整行统计和第二遍，
收益与复杂度需要实测。

### 方案 B2：单行/小 N 特化

当一个处理单元能保留完整行所需的 activation 时，可在统计后直接量化，减少
activation 的 GM 往返。这并不自动消除 Cube accumulator 到 GM 的写入；后者
还取决于 Matmul 输出接口和跨核数据通路。仅一个不覆盖完整 N 的 Cube tile
放入 UB 并不足以完成完整行量化。
当前代码已有 `N <= VECTOR_TILE_N` 的 activation
复用；下一步应通过 profile 判断是否扩大该路径，而不是盲目增大 tile。

如果将 N 拆到多个跨核 owner，需要处理 partial row max 归约、同步和第二阶段
量化；直接使用局部 max 可能改变输出。因此该方向应先设计并验证完整协议。

## C. row max 与量化流水

一个常见且可研究的结构是先做行统计、再量化；并非所有 DynamicQuant/vLLM
版本都已在本次审阅中证实采用相同实现：

1. 向量 abs/ReLU + ReduceMax；
2. 计算 scale/inverse-scale；
3. 向量除/乘 + Cast + clamp。

对本算子的一种候选组织方式是：

1. Cube tile → FP32 scale 广播 → ReLU，并在同一 tile 做 max；
2. 跨 tile 合并 row max；
3. 输出 scale 后重新消费保留 tile 或 workspace；
4. 向量量化写回。

一个需要测量的重点是第二遍对 GM 的读取和中间结果保存成本；不能仅因更换
`ReduceMax` API 名称就推断会有收益。
GroupedMatmul 的 per-token scale buffer 和 FFNQuant 的 queue/workspace 组织是
当前可以对照的实现之一；是否适合当前 shape 和数据流需要实测。

## D. 需要验证后再决定的方案

- `QUANT_VECTOR_ONLY=1` 可作为性能消融；其结果不能单独证明 exact INT8 正确性。
- vLLM/CUDA 的 `nearbyint`、float-to-int8 转换需要与 AscendC 的目标转换语义
  对照，不能直接当作等价依据。
- 仅把 Compare/Select 加入现有循环，可能增加 mask、barrier 和 UB 流量；需测量
  它是否实际减少 scalar exact correction。
- Fixpipe 是否适用取决于输入 scale 是否已知、目标产品和具体接口；动态 row max
  场景需要先解决 scale 产生和应用的时序。
- N=128 或两 tile cache 的采用与否应由对应 shape 的重复基准和正确性测试决定。

## E. 建议记录的指标（视工具可用性）

```text
端到端时间（题目口径）
Task Duration / task_cycles
Cube、Vector、MTE2、MTE3 利用率（msprof 或等价工具）
workspace bytes / GM read-write bytes
CrossCore wait/set 次数
row-max tile 数、fallback lane 数、exact correction 数
INT8 mismatch、yScale max diff、zero-row/half-boundary 结果
```

诊断计数可能扰动性能，应与正式计时版本分开。CAModel cycles 和设备端到端时间
是不同指标；无法取得的硬件计数应注明缺失，而非用其他指标冒充。

本项目当前建议：候选在正式/增强回归通过，并在目标 shape 集合上显示稳定收益
后再替换正式根版本；否则保留历史基线并把候选放在 `op/` 或实验分支。这里是
工程管理规则，不是参考项目本身的结论。
