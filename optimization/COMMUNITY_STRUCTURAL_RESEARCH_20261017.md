# 社区算子结构检索与本题适配（2026-10-17）

## 基线与证据边界

- 当前根 SHA256 `fade9cbe23d05ffd5b636015b2c59c4e4f9bf63987bd3b4c370624d545ff9f62`，正式提交 `6ad2ed99193e507d8e278978`，15/15、score 16.07。
- 当前执行路径：persistent M×N AIC tile grid（64×256）→完整 INT32 GM 矩阵→`SyncAll<false>()`→AIV 完整行量化。不是异步 Cube/Vector 流水。
- 正式点 12–15 的 shape 尚未知，不能因点编号/耗时递增就断言它们对应大 M、大 N 或大 K。阶段瓶颈也未直接测量。
- 本地已有 tile16 对照：64×256×256 的 task_cycles 140252→42499；64×1024×256 为 66178→23747，所述输入严格 INT32 golden 下 INT8 mismatch=0、scale 差=0。这些是已有诊断数据，不是本次新设备测量，更不是官方收益。

## 已检索并阅读的实现

固定 CATLASS 镜像 revision：`b71539e306ca29f82a6f55282e867b8a1f8e0b97`。

1. [103 W8A8 per-token/per-channel kernel](https://github.com/mirror-cann/catlass/blob/b71539e306ca29f82a6f55282e867b8a1f8e0b97/examples/103_dynamic_optimized_quant_matmul_per_token_basic/impl/kernel/per_token_matmul_kernel.h)
   与本题相近的 INT8 输入、INT32 accumulator、行/列 FP32 scale。采用 1:2 CV、workspaceStages=2、preloadStages=1、L1/L0A/L0B 双缓冲和 ShuffleK。
   [具体 producer/consumer](https://github.com/mirror-cann/catlass/blob/b71539e306ca29f82a6f55282e867b8a1f8e0b97/include/catlass/gemm/kernel/dynamic_w8a8_matmul_per_token_per_channel_dequant.hpp)
   使用 per-core 两级 GM 环形 tile，AIC 写完释放 ready flag、AIV epilogue 完成释放 free flag；覆盖 slot 前必须等待消费者。
   **不等价点**：其输出 FP16；没有本题 ReLU 后全行动态最大值、INT8 RNE 再量化。不能用 FP16 epilogue 直接替换本题计算。
2. [44 quant_matmul_full_loadA_tla 设计](https://github.com/mirror-cann/catlass/blob/b71539e306ca29f82a6f55282e867b8a1f8e0b97/examples/44_quant_matmul_full_loadA_tla/44_quant_matmul_full_loadA_tla_en.md)
   INT8 A[M,K]、B[N,K] 与本题一致，A 的 `tileM×K` 常驻 L1，B ping-pong，不同 N tile 复用 A。其报告设备 910B1、CANN 9.0，但输出 BF16，报告收益不属于本题。
3. [CATLASS matmul 模板总结](https://catlass.readthedocs.io/en/latest/2_Design/01_kernel_design/04_matmul_summary)
   已有 09/22 MultiCoreSplitK、25 FullLoadA、31 SmallMatmul、34 SingleCoreSplitK、padding/BlockND/NZ、preload、ShuffleK。文档为 mutable latest。Split-K 以 MN tile 不足、K 足够大为条件；并非对所有大输入启用。
4. [ops-nn DynamicQuant 多行 kernel](https://github.com/mirror-cann/ops-nn/blob/acfc1342574ce6631d66b5e2e6dfdd00d878ce21/quant/dynamic_quant/op_kernel/dynamic_quant_multi_row.h)
   多行 UB tile + WholeReduceMax + broadcast，代替逐行标量控制流。
   [长行 double-buffer kernel](https://github.com/mirror-cann/ops-nn/blob/acfc1342574ce6631d66b5e2e6dfdd00d878ce21/quant/dynamic_quant/op_kernel/dynamic_quant_large_shape_opt.h)
   显式两遍长行扫描与预取。其 abs-max/smooth 等语义不能直接替代本题 ReLU 后 max。
5. [asc-devkit 高性能 Matmul 样例](https://github.com/mirror-cann/asc-devkit/blob/master/examples/01_simd_cpp_api/05_best_practices/01_matrix_compute/matmul_high_performance/README_en.md)
   MDL 的 L1 depth/step 配套、constant tiling、UnitFlag 示例；现有代码已使用 MDL，不能把“启用 MDL”当作新改动。其测量为独立 FP16 GEMM，不用于预测本题 score。
6. [Triton-Ascend CV fusion 指南](https://github.com/Ascend/triton-ascend/blob/main/docs/en/programming_guide/cv_fusion_operator.md)
   tile epilogue、sub-block 切分、跨 tile 状态的 workspace/sync 约束。不能移植 Ascend950 的直接 L0C→UB/SIMT 代码来假定 dav-2201 可用。

以上均仅借鉴结构；未将第三方源码复制进提交 kernel，也未新增外部依赖。后续如复制代码需另查许可证与服务器构建约束。

## 优先结构 A：分块 CV 流水 + 多行 epilogue

```
AIC: GEMM tile -> ring[core][slot] INT32 -> ready(slot)
AIV: wait ready -> INT32→FP32 -> ×tokenScale -> ×channelScale -> ReLU
     -> batched row partial max -> activation GM tile -> free(slot)
all cores: documented global barrier (all producer and consumer loops drained)
AIV: reduce partial max per row -> yScale -> parallel N tiles RNE/clamp -> y
```

- 环形 workspace 只需 `stages×cores×tileM×tileN×4`，不再需要完整 INT32 矩阵。
- **仍需要完整 FP32 activation 暂存，或者重算 GEMM。partial max 并不能单独消除所有完整中间矩阵。** 激活暂存与 max 暂存是需要计入的真实开销。
- 当前 `N<=4096` 时原实现已在 UB 保留整行激活，不应声称现有所有情况都二次读 INT32。
- 最大潜在收益来自 Cube 与缩放/ReLU/max 重叠、多行广播归约减少逐行 V↔S 同步，以及第二阶段量化可沿 N 进一步并行；不是凭空减少到一次 GM 访问。
- 风险/验证：同一 ready/free 的双向 event 编号不冲突；producer tail、idle core、slot 回绕有一致任务数；AIV 写激活/partial max 后在全局 barrier 前有完成序；所有 AIC 都必须排空 free wait 再到 barrier，不能一部分 core 提前退出。
- 对照：先仅实现单 slot 顺序握手，确认严格数值/退出，然后双 slot；保留现有 ExactQuant 边界修复，先不要同时改数值算法。

## 优先结构 B：完整行组 ownership + UB 驻留

当 M 足够分满核，且若干完整行及量化 scratch 可放入 UB：每组 AIC 计算一个小 M 行组的全 N，AIV 用 UB 保存激活并做全行 max，随后原地量化。用 paired events 而不是全矩阵 SyncAll，让各核独立推进下一行组。

- 与历史完整 N 单核分区不同：调度单位是可重复推进的行组，不是先算完整大 M 分区才消费；必须确实实现 ready/free 和双 slot 才有异步重叠。
- 有机会去掉 FP32 activation GM 暂存、减少全局同步；dav-2201 仍可经 GM 小 ring 交接 INT32，不能假定直接 L0C→UB。
- 仅当 M 行组数足够、N 满足 UB 预算使用。小 M 大 N 退回结构 A，否则牺牲 AIC 并行度。

## 条件结构 C：真正的跨核 Split-K

若 `ceil(M/tileM)×ceil(N/tileN)` 远小于核数且 K 足够大，把任务扩展为 `(mTile,nTile,kSplit)`，每个 split 写独立 INT32 plane；barrier 后 AIV **先 INT32 模 2^32 合并，再转 FP32**，然后按原语义缩放/量化。

- 这与目前同一个 AIC 串行执行的 <=65536 K chunk 不同；后者保护溢出语义，没有增加 K 方向核并行。
- 不允许各 split 先转 FP32 再求和；不允许靠未初始化 GM atomic 作为跨核归约。
- split plane 写回及 Vector INT32 归约会增加流量。仅针对核数不足的 shape，不能因 K 大就无条件使用。

## 条件结构 D：A 常驻 L1 + grouped swizzle/preload

当 `tileM×K` 及 B 双缓冲符合实际 L1 预算，让同核连续执行相邻 N tile，复用 A；不再每次 `IterateAll<true>` 都独立搬运/建立状态。大输入不满足 full-load 时退回 K panel 常驻与 preload。

- 更改 task 顺序本身并不保证 MatmulImpl 保留 A；需要可核验的 L1 tile 生命周期或改成显式 DataCopy/Mmad。
- 先测 MTE2/Cube/Scalar 活跃与等待，不预设这一结构会解决官方点 12–15；需要形状映射或代表性大形状实测。

## 本轮隔离对照

`optimization/candidates/mix-2d-tile16-persistent/` 仅将当前 root 的 tileM=64 改为 16，其他 kernel 字节不变；它是任务粒度消融，**不是上述 A/B/C/D 的完成实现**。

- 主工程 CANN 9.1.0/dav-2201 Release 编译通过（build-release）；host/source 检查通过 360 ownership + 8 K chunk，SHA256 `cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`。
- 配置失败记录：最初没有 ASC 环境，随后 sim 模式未指定 CMAKE_ASC_ARCHITECTURES；均为构建配置错误，不是设备 kernel 失败。保留独立日志，不修改根 build。
- 未取得本候选正式结果，不修改当前根或最高有效版本。新设备 smoke 的状态以候选 RESEARCH.md 为准，不继承历史诊断的通过范围。
