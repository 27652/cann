# Multi-row VectorStage candidate v1

## Hypothesis

The current official root (`tileM=16` persistent MIX, score 16.66) performs
the AIV epilogue one complete row at a time. This candidate applies the
community pattern shared by ops-nn DynamicQuant, Triton fused reductions and
CPU SIMD kernels: keep a complete row group in UB, perform vector cast/scale/
ReLU, reduce several rows with `ReduceRepeat<MAX>`, then reuse the activation
tile for the existing exact quantization path.

The first implementation is deliberately conservative:

* only INT32 matmul;
* only resident channel scales;
* only `N <= 4096 / QUANT_MULTI_ROW`;
* only complete groups of 2/4/8 rows;
* incomplete groups and wide rows use the unchanged scalar-row path;
* no new cross-core ownership, event protocol, workspace, or launch.

`QUANT_MULTI_ROW=1` is the control build. The experimental default is 4 in
this isolated candidate, not in the root.

## Current status

The source is isolated from the verified root. No formal submission and no
root replacement have been performed. All five CANN 9.1 / dav-2201 targets
(runner and rows=1/2/4/8 benchmark) compile. Strict INT32 CAModel checks passed:

* rows=1 control and rows=4 grouped path, shape `129x513x65`, signed scales,
  injected zero rows, non-multiple group tail: zero INT8 mismatches and exactly
  matching recorded yScale (`results/rows4-tail-20261017/summary.json`).
* rows=2/4/8 grouped paths, shape `193x17x33`, deliberately constructed
  half-integer quantization values: zero INT8 mismatches and exactly matching
  yScale (`results/grouped-half-small-20261017/summary.json`).
* rows=1 control and rows=4 build with `N=1025` wide-row fallback,
  shape `17x1025x33`: zero INT8 mismatches and exactly matching yScale
  (`results/wide-fallback-20261017/summary.json`).

An earlier larger half-integer attempt (`129x257x33`, all rows variants) ran
past the 120-second outer tool window. Its CAModel process was explicitly
stopped, no result was recorded, and its partial log remains in
`results/grouped-half-20261017/`; this is a timeout, not a kernel failure.
The smaller half-integer regression replaced it for semantic checking.

No performance comparison has been run. Group staging reuses existing 4096-lane
buffers; only reduceOutBuffer grows from 32 to 128 bytes (+96 allocated bytes).
Score impact and dispatch profitability are unknown. Targeted host invariants
and final source review remain before a Fast Track submission; device smoke or
performance evidence is not a repository-mandated submission prerequisite.

## Risks

The local CANN 9.1 headers expose `ReduceRepeat<ReduceType::MAX>` while older
documentation calls the same family `WholeReduceMax`. The exact repeat stride
and output layout must be confirmed by compilation and strict output checks.
The group path uses a compile-time-sized C++ array and LocalTensor slicing for
contiguous row groups. Compilation and CAModel confirmed these for tested row
counts 2/4/8, but do not prove all legal shapes or hardware behavior.

It is not evidence that a CV ring or asynchronous Cube/AIV pipeline has been
implemented. Fallback density, AIV-only cycles and reduction-event counts have
not been measured. Wide-N fallback, tiny scales, large K and FTZ remain untested
for this source revision.

## 多行候选正式反馈（2026-10-17）

- 已使用 `/tmp/opencode/cookie`，由受控 CLI 自行读取认证；动态 editable 清单为 `kernel.asc`。
- 首次提交 `6ad32e78193e507d8e8b06a6`：Compile Error，服务端缺少本地 9.1 的 `ReduceRepeat<ReduceType::MAX>` API。证据及完整恢复工程：`evidence/formal/multi-row-v1-compile-6ad32e78/`。
- 新修订仅将两次调用改为 `WholeReduceMax`（本地头文件确认其转调相同内部实现），五个构建目标编译成功、3584 组主机布局检查通过；未对新修订重新运行 CAModel。kernel SHA256 `54ab681272f6b223e216d0deea14de8aa151c6626358ec80a4160eb24e4f46e5`。
- 新提交 `6ad32f9e193e507d8e8cf57c`：Wrong Answer，12/15 通过；按正式结果顺序 case 1/3/8 失败，precision_ratio 分别 0、0.5339366515837104、0.019049067815879006；其余 12 点为 1。同 ID 榜单 score 0，不是有效成绩。证据及服务端完整返回工程：`evidence/formal/multi-row-v1-wrong-6ad32f9e/`。
- 失败机制尚未定位：可能涉及 reduction 布局、同步或组内 activation 生命周期；不能仅凭错误分布断定 stride 错误。正式 case shape 未知。新修订本地 smoke 未重跑，不能继承旧修订设备验证状态。
- 两次均未晋升，根未修改；历史最高有效仍为 16.66。停止提交当前失败 payload，下一步做最小逐行 reduction 消融以隔离批量激活与归约布局，不再等待完整 CAModel 性能回归。原始 API 回包位于 `/tmp/opencode/multi-row-{v1,v2}-formal-result*.json`，持久目录只保留脱敏字段和源码。
