# 社区算子实现补充研究：CUDA/Triton/CUTLASS 与 Ascend TileLang

更新时间：2026-10-17。本文只记录结构借鉴和适配判断，不把第三方
实现的性能或数值语义直接套用于本题。

## 本题的不可改变语义约束

目标算子不是一般的 W8A8 dequant 或 absmax quantization，而是：

```text
INT8 A/B -> INT32 dot accumulation -> FP32
         -> x1Scale * x2Scale -> ReLU
         -> per-row max -> yScale=max/127 (zero row => 1)
         -> divide -> RNE -> INT8 clamp
```

因此以下实现中的 `absmax`、FP16 输出、先量化后 matmul、近似 reciprocal
或硬件默认转换，只能作为性能结构参考；不能直接替换当前严格 golden
语义。当前最高有效正式结果仍是 tileM=16 persistent MIX，score 16.66。

## 新增检索结果

### 1. TileLang Ascend INT8 Cube + Vector fusion 示例

入口（社区镜像/技能页，需回到原仓库核对 revision 与许可证）：

- `https://github.com/xchang1121/op-autoresearch/tree/main/skills/tilelang-ascend/examples/tilelang-ascend-example-quant-matmul`
- 说明页：`https://skills.rest/skill/tilelang-ascend-example-quant-matmul-xchang1121`

公开描述中的结构是 `T.gemm_v0` INT8→INT32、workspace index、Cube/Vector
自动融合，以及 `AUTO_CV_COMBINE` / `AUTO_CV_SYNC` pass。这个方向比一般
CUDA 资料更接近本题的硬件数据流。

**可借鉴：**

- 让编译器/tiler 明确知道 workspace producer-consumer 关系，而不是把
  完整中间矩阵和同步都隐含在 host 侧；
- 将 INT32→FP32、scale、ReLU 和输出转换作为同一 CV epilogue 设计；
- 用编译器生成的 CV pairing/sync 作为 row-ring 手写 event 协议的对照。

**限制：**

- 资料说明主要面向 Atlas A2/A3；不能证明 dav-2201/CANN 9.1.0 支持同样
  的 TileLang pass 或 workspace 语义；
- 示例是 dequant 到 FP16/混合精度，不包含本题的 row-max 后 yScale、RNE
  和 INT8 输出；
- 不能引入 TileLang 作为正式 payload 依赖，除非赛事模板与编译环境明确
  提供它。

建议：只把其 workspace/自动 CV 调度抽象作为实验设计参考，先查当前环境
是否安装对应 compiler/API，再做最小编译探针；不要直接移植生成代码。

### 2. vLLM `scaled_quant.cu`：向量化 row quantization

来源：
`https://github.com/vllm-project/vllm/blob/main/csrc/quantization/w8a8/int8/scaled_quant.cu`

本轮实际读取了该文件的 mutable main 源码，未固定 revision。
其 dynamic kernel 对每行使用固定 block，向量化读取，先做 block reduction
得到 max，再将 scale 放入 shared memory，第二遍向量化读取并使用硬件
RNE/saturating conversion 写 INT8。该实现还使用 16-byte 对齐路径，并把
quantization 变成规则的 vector loop，而不是每个元素调用 scalar helper。

**对本题的启发：**

- AIV 可采用“行组一次加载、局部 max、广播 scale、向量转换”的布局；
- 当前根已默认启用 vector RNE + packed boundary mask + sparse exact
  correction（`kernel.asc:764–861`）；不能将此社区模式当作全新方案。
  全元素 scalar loop 只在非 mask fallback 条件下执行，未测得其占比；
- 对齐的 N 主路径和 N-tail fallback 分开，避免主循环反复 mask/分支；
- row max 与量化分成两个明确阶段，共享 UB/片上缓存而不是重新走 GM。

**不能直接照搬：** vLLM 使用 absmax/127 和 `127/absmax`，本题是 ReLU 后
最大值、逐行 `max/127`、并且要求题面定义的 FP32/RNE 行为。应先实现
“vector fast path + 保守 exact fallback”诊断版，边界不满足误差证书时整
个 tile 回退，不能用随机通过代替证明。

### 3. Triton fused softmax 与 persistent matmul

来源：

- `https://triton-lang.org/main/getting-started/tutorials/02-fused-softmax.html`
- `https://triton-lang.org/main/getting-started/tutorials/09-persistent-matmul.html`

fused softmax 的关键不是 softmax 本身，而是一个 program 负责完整行或行组，
在 SRAM 中完成 load、reduce、broadcast 和 store，避免多个 kernel/GM 往返。
其 persistent matmul 则让固定数量的 program 循环消费 tile，使用 grouped
M/N swizzle 改善 cache 和负载均衡，并把 epilogue 放在 tile 生命周期内。

**对本题的启发：**

- 对 `N` 能放入 UB 的形状，尝试完整 row-group residency：Cube 写小 ring，
  AIV 一次完成 max 和量化；
- 对大 N，使用两阶段 row-group：第一阶段保留 row max/activation，第二阶段
  沿 N 规则化量化；
- 用 persistent tile counter/静态任务循环减少小 M 下的 launch/task 调度
  开销；当前单 launch 约束使这一思路尤其 relevant；
- 采用 grouped swizzle，让同一 A block 连续处理多个 N tile，尝试复用 A
  的 L1/搬运状态。

**Ascend 映射风险：** Triton 的 SRAM/register tile 与 Ascend 的 UB/L1/L0C
不是同一层次；CUDA block 内隐含 barrier 不能替代 AscendC 的 AIC/AIV
cross-core flag。只能移植任务顺序和生命周期，不移植同步假设。

### 4. CUTLASS Epilogue Visitor Tree / GEMM+reduction

来源：

- `https://research.colfax-intl.com/epilogue_visitor_tree/`
- `https://github.com/NVIDIA/cutlass/blob/main/include/cutlass/epilogue/threadblock/fusion/visitor_store.hpp`
- CUTLASS `35_gemm_softmax` 示例：`https://github.com/NVIDIA/cutlass/tree/main/examples/35_gemm_softmax`

EVT 的价值是把 GEMM 后的 elementwise、row reduction、broadcast 和 store
组织为可组合 epilogue。本轮实际读取了 `35_gemm_softmax/gemm_softmax.cu`，
其中有按 N block 数分配的 partial norm/sum workspace；未能获取其内部
`gemm_with_softmax.h`（网络超时），因此尚未核实内部归约和 launch 数量。
它不是已确认可直接满足本题单 launch 的融合实现。

**对本题的启发：**

- 把本题拆成可验证的 epilogue visitor：`CastI32Fp32`、scale、ReLU、
  `RowMax`、`ScaleBroadcast`、`ExactOrFastRNE`；
- 对 N-split tile 保存每行 partial max，使用确定的 row owner 做最终 max，
  不让不同 Cube split 直接写同一 yScale；
- 将 activation 暂存、partial max 和 final quantize 的生命周期显式列入
  workspace 预算，而不是认为“partial max 就消除了完整中间矩阵”。

**限制：** CUTLASS 依赖 CUDA warp/block primitives；本题必须保留 INT32
累加及 Ascend event/SyncAll 语义，EVT 只能作为设计图，不是可移植代码。

### 5. TensorRT-LLM / CUDA quantization helpers

本轮通过 GitHub API 获取了 `quantization.cu`（blob
`f6cf680530940edbabadb598909ca1b50df470f1`）。其
`invokePerTokenQuantization` 明确选择 shared-memory 缓存完整行，容量不足
时退回 reload；每行一个 block，packed uint4 加载有列数整除要求。
内部 `quantization.cuh` 获取超时，未核实其具体数值指令。

对本题最值得验证的是 **vector width 与 tail 分派**，而不是具体 scale
公式：N 对齐主路径使用 16B/32B load，尾部单独使用 mask；scale 为零行时
显式写 1；任何可能改变 FP32 乘法/除法顺序的融合都必须重新跑严格 INT32
golden。

## 建议实验优先级

1. **多行 AIV epilogue（最高优先级）**：参考 ops-nn DynamicQuant 的
   WholeReduceMax/broadcast，对 2/4/8 行批处理 cast、双 scale、ReLU 和
   row-max，减少逐行 V↔S 同步和指令启动；保留当前 sparse exact correction。
   先只改 VectorStage，与 16.66 基线做同输入配对。
2. **tile-level CV producer/consumer**：与已提交的完整 N row-ring 区分。
   保留二维 Cube tile 并行，AIV 消费 tile 并写 FP32 activation/partial max，
   barrier 后沿 N 分派最终量化。必须核算完整 activation 暂存流量。
3. **persistent grouped tile scheduler**：对大 K 或小 M 形状尝试静态 tile
   counter + A-reuse swizzle；仅改变 task order，不先改算术。
4. **跨核 Split-K**：只在 MN tile 数不足核数且 K 足够大时研究，参考
   CATLASS Split-K。先 INT32 合并再转 FP32；它与 N-split partial-max 是
   两种不同归约，不混用条件。预计同步与 workspace 风险较高。
5. **量化消融而非重新发明 mask**：统计已有 boundary mask 密度、fallback
   行数、V↔S 等待；再决定是否值得研究向量整数精确修正或压缩危险元素。

## 结论

目前最值得继续的组合是：**TileLang 的 CV workspace 抽象 + Triton/CUDA 的
row-wise vector reduction + CUTLASS 的 epilogue decomposition/persistent
tile scheduling**。当前 mask 快路径已存在，下一轮优先研究多行 epilogue，
再研究保留二维并行度的 tile CV 流水。row-ring 官方 15.71 仅证明该具体
候选没有提高总 score，不能单凭这个结果证明 CV 流水无效或量化就是瓶颈。
以上均未新增设备测量，未复制第三方代码，也未改变当前根实现。
