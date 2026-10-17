# 第一阶段：结构消融（2026-10-17；不提交）

## 身份与范围

- 基线快照 `source/baseline.asc`：SHA256 `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`。
- 单一运行时分派二进制 `build/bench_upper_bound`：SHA256 `655a0e284358fb5d2291872c1b79b4dcb0fa3d53e980177c1b4af114db2285f1`。
- CANN 9.1.0 / Ascend910B1 / dav-2201 / Release。完整源码身份见 `source-identity.json`，每次输入、golden、脚本和环境见各运行 `fingerprint.json`。
- 模式：0 baseline；1 INT8 65536-K chunk（原 M ownership）；2 保留 mask 工作、跳过 scalar correction；3 synthetic 单行 M 分区；4 synthetic N 分片、局部量化。
- 根 kernel 和冻结文件未改动；无 POST、无晋升，无需执行晋升 commit。其他流程的工作区变更不包含于本实验。

## 已完成：窄 shape 同身份消融

`results/narrow-v1/`，shape `(2,1025,32)`，seed 20261017。四侧 fingerprint 完全相同。

| 模式 | cores / singleM / N | task_cycles | 相对 baseline | INT8 mismatch | scale |
|---|---|---:|---:|---:|---|
| baseline | 1 / 2 / 1025 | 39486 | — | 0 | 相等 |
| no scalar correction | 1 / 2 / 1025 | 35186 | -10.890% | 0 | 相等 |
| M-split synthetic | 2 / 1 / 1025 | 35153 | -10.974% | 0 | 相等 |
| N-split synthetic | 17 / 2 / 64 | 29070 | -26.379% | 863 | 失败，max abs diff 7.38906765 |

该点支持 B（scalar correction）和 C（并行度）均有可见优化空间，不能据此认定其中之一主导，更不能外推正式 shape。mode 2 保留 mask 构造与同步，并非完整 approximate-only Vector 上界。N-split 改变 tile 宽度和量化工作量，尚无全局 row max、唯一 yScale 写者和全局 second pass，不能视为可实现加速比，更不能提交。

## 大 K 状态

- 初次 `results/common-4x64x65536/0/` baseline 在 180 秒墙钟超时，无完整 task duration、无输出、无有效比较；历史脚本未捕获 timeout，stdout 未保存。输入/golden 和不完整 dump 保留，不能拿这些推断 A/D 耗时。
- `K=32768` 的新任务只能作为 chunk 调用控制（baseline 已是 INT8，不是 FP32）；不能用于声称消除了大 K FP32 路径。
- `results/all-k-v1/0/` 在启动模拟器前遇到 `host CAModel lease busy`，属于未运行，不是数值失败或超时；mode 1/2 也未运行。未抢占锁、未重试或绕过互斥。
- `results/common-1x2x65536-v2/` 完成了同一输入、同一环境、同一二进制（完整 fingerprint 相等）的真实大 K 对照：baseline(mode 0) `181708` cycles，all-K INT8 chunk(mode 1) `64830` cycles，no-exact(mode 2) `181708` cycles；三者均 `int8_mismatches=0`、`scale_ok=true`、scale max abs diff=0。相对 baseline，mode 1 为 `-64.322%`（约 `2.803x`）；mode 2 为 `0%`。workspace 分别为 `17563656 / 16777224 / 17563656` 字节，三者 cores=1/singleM=1/N=2。仅支持 FP32 conversion/Matmul 与 GM workspace 联合路径（A/D）存在空间，不能拆分阶段归因。
- **覆盖限制**：该随机输入两个输出均为零、yScale=1，不能有效证明正累加、chunk 寻址或 atomic 正确；K=65536 也没有跨 chunk 累加。mode 2 在零行上相同不说明正输出 exact correction 没有收益。该点仅为严格 INT32 golden 的弱覆盖设备比较，不等于 all-K 候选已通过广泛回归或正式评测。
- 下一步 A/D 对照应使用 `K>=65536` 的小 M/N。同一二进制只改变 mode，分别报告联合路径收益；尚无独立 GM 与 Matmul 阶段计时，不分摊这两个阶段。

## 风险与门槛

- mode 1 尚不是可提交候选：缺少真实 K chunk tail、atomic wrap 与多核大 K 设备验证；mode 4 则是明确错误的 synthetic 实现。
- 未完成第二阶段 all-K 严格大 K 回归、第三阶段正确 N-split protocol 或第四阶段批量 exact correction。
- 修复后的 runner 拒绝覆盖已有结果目录、保存 timeout failure 和完整 fingerprint，并使用共享 CAModel lease；初次运行只做了进程检查，未持有 lease，此差异保留。
