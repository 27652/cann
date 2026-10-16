# 以最优用时为目标的执行路线

## 项目目标（当前工程定义）

如果以竞赛提交为目标，建议不要只优化某一个 CAModel case，而是关注：

```text
在题目 15 个测试点全部正确的前提下，改善各点正式计时用时，
以题面规定的平均得分评价整体提交性能。
```

题面给出的评分形式为 `100 / (1 + log_1.5(t/T))`；按该规则，评估时可以同时
考虑小形状的启动/同步成本和大形状的 Cube/Vector 吞吐。实际评分仍以正式评测
环境和题面规则为准。

其中 `t` 是当前提交用时，`T` 是该点最优用时，不是拆分算子的基线时间。
题面另有与拆分基线比较的文字，最终实施口径仍需以评测系统确认为准。
非线性评分的均值不等于平均用时的函数；平均用时下降、每点均不回退、得分提高
是不同条件。应逐点计算评分变化，不能把“所有点不回退”当作数学上的必要条件。
“最优用时”是优化目标，并非已有全局最优性证明。

## 阶段 0：建立可信基线

- 保存 `op/kernel.asc`、`op/kernel_v2.asc`、`op/kernel_v3.asc` hash。
- 若能取得正式环境，以题目 CANN 版本和实际计时范围复现 prior、v3、当前 safe
  kernel；若不可取得，明确记录本地与正式环境的差异。
- 分离 H2D/D2H、kernel task、同步和日志开销；CAModel 结果只作结构归因。
- 记录可取得的 shape 的 M/N/K、scale 分布、zero row 比例和 tail 情况。
  正式 15 点输入尚未公开，本地自建 15 点不能代替正式点，也不能据此声称正式通过。

## 阶段 1：数据流优化候选（尚无统一收益结论）

以下是候选研究顺序，可以根据 profile 改变；跨核流水不必然比量化校正改动风险低：

1. 以 GroupedMatmulQuantMixCore/FFNQuant 为参考，做 Cube tile → Vector tile
   的 AIC/AIV 流水；验证 workspace 写入是否可以延迟或减少。
2. 扩大“小 N/整行可驻留 UB”特化，只在 profile 显示收益时采用。
3. 优化 per-row/per-channel scale 的一次加载、广播和复用。
4. 重新评估双 buffer、tile size、M/N core ownership；每项保留独立日志。

本项目建议每一步都检查所有 15 点及极端/tail/zero/negative-scale/large-K/
multi-core 回归，并记录目标 shape 的重复测量结果；是否达到提交门槛应按正式
评测规则和实际收益判断。

## 阶段 2：向量化 exact correction

制作独立候选，不直接修改正式 `kernel.asc`：

1. 先建立可支持的误差界或精确判据，再以 Compare 生成风险 mask；
2. CreateVecIndex 生成原始索引，适配 pattern 后用 GatherMask 分别筛选元素及索引；
3. 向量整数乘积/余数检查或批量 exact correction；
4. 通过保留的原始索引写回（CreateVecIndex 本身不恢复位置或执行 scatter）；
5. 对安全 lane 使用向量 RNE，风险 lane 使用 exact 结果；
6. 对风险数量从 0、1、稀疏到全命中做性能分桶。

建议覆盖：精确 reciprocal、非精确 reciprocal、半整数两侧、tie-even、
tiny/subnormal scale、负 scale、零行、INT8 极值、N tail、极大 K；具体覆盖
集合还应与题面允许的输入域保持一致。

## 阶段 3：必要时重构 row-max ownership

如果 profile 表明该方向可能带来足够收益，再研究 N 维拆分：

- 第一阶段各 owner 输出 partial row max；
- 通过 workspace/同步做完整 row max reduction；
- 第二阶段所有 owner 使用同一个 row scale 量化；
- 处理跨核 barrier、尾块、输出写入和负/零行。

若题目定义要求完整行最大值，则不能用局部 max 直接替代最终 yScale；部分最大值
需要先完成跨 tile/跨核归约。

## 合入门槛

对于本项目，建议候选版本在满足以下条件后再成为正式版本：

- 题目规定的全部测试点通过；
- INT8 输出满足题目规定的精度要求（当前工程若采用完全一致作为保守门槛，应
  明确这是本工程策略）；
- yScale 在题目允许范围内；
- 候选依赖的 reciprocal/Compare mask 等关键语义已在目标环境中得到支持证据；
- 目标 shape 集合的用时改善具有重复性，且没有不可接受的回归；
- 编译、CAModel、实际设备（若可用）之间的结果和性能差异已被记录；
- 所有 benchmark 结果带源码/二进制 hash、输入 profile 和计时范围。

当前策略仍是 INT8 与可信参考完全一致。题面要求与 CPU 对齐、rint、round 后
clamp，但精度表未单列 INT8 容差，因此不能推断允许 ±1，也不能声称已核验评测器
的精确判定方式。yScale 按题面 FLOAT32 要求与实际 checker 核对。一次回归通过
是输入集上的证据，不是全部合法输入正确性的穷尽证明。

若性能没有稳定提升，或正确性证据不足，当前工程可保留 `op/kernel.asc` 历史
基线；候选只保存在 `op/kernel_v*.asc` 和 `reference` 分析中，不覆盖可回退版本。
