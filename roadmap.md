# QuantMatmulReluQuant：文件导航与当前状态

更新时间：2026-10-17。本文按用途列出源码、文档、版本身份和可复核证据；自动生成的输入、输出、编译缓存与 CAModel dump 不作为源码版本依据。


## 最新正式状态（2026-10-17，tileM=16 persistent MIX）

- 当前根及最高有效：`6ad31941193e507d8e654e7b`，正式 15/15，score **16.66**。
- kernel SHA256：`cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`。
- 正式证据及完整恢复：`evidence/formal/tile16-persistent-6ad31941/`。
- 候选与严格 smoke：`optimization/candidates/mix-2d-tile16-persistent/`。
- 晋升前 16.07 根快照：`optimization/snapshots/pre-tile16-persistent-16.07/`。
- 以下“最新/当前”属于历史时点；数值与同步等残余风险见 `report.md` 晋升条目。

## 最新正式状态（2026-10-17，03:38 UTC，单次 launch 二维 MIX）

- 当前根及最高有效：`6ad2ed99193e507d8e278978`，Pass 15/15，score **16.07**；kernel SHA256 `fade9cbe23d05ffd5b636015b2c59c4e4f9bf63987bd3b4c370624d545ff9f62`。完整恢复与 validate/decide 证据：`evidence/formal/mix-2d-single-launch-6ad2ed99/`；前一 14.94 版本：`evidence/formal/fast-track-6ad2e531/`，晋升前完整根快照：`optimization/snapshots/pre-mix-2d-single-launch-14.94/`。
- 候选入口 `optimization/candidates/mix-2d-single-launch/`：一个 MIX 1:1 kernel，二维 AIC task grid、`SyncAll<false>()` 全核同步和完整行 AIV 量化；主工程/benchmark 编译成功，360 ownership + 8 K-chunk 主机检查和三个严格 INT32 CAModel smoke 通过。残余边界风险与单次测量限制见其 `RESEARCH.md` 及 report 晋升条目。后文“当前/最新”均为历史时点。

## 历史正式状态（2026-10-17，02:43 UTC，直接 CLI）

- 当前根及最高有效：`6ad2e0a8193e507d8e164f44`，Pass 15/15，score **14.71**；kernel SHA256 `e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea`。证据与完整恢复：`evidence/formal/fast-track-6ad2e0a8/`；旧最佳 `fast-track-6ad2dbba/`，旧根快照 `optimization/snapshots/pre-aggressive-combined-14.66/`。
- 组合候选 `optimization/candidates/aggressive-combined/`：全 K INT8 + 同步 row-job + 单元素免 workspace；已有编译/主机检查，本地设备验证未完成，风险见 report 最新条目。以下“当前/最新”均为历史时点。

- all-K INT8 新隔离实验入口：`optimization/candidates/int8-all-k-safe/`、`int8-all-k-128k/`、`int8-k-split-no-atomic/`，各自 `RESEARCH.md` 记录源码/构建身份与已运行的弱覆盖 boundary smoke。未正式提交、未晋升；仍需正输出/溢出有效设备测试，详见 report 对应条目。

## 最新正式状态（2026-10-17，Aggressive Coordinator）

- 组合候选入口：`optimization/candidates/aggressive-combined/`，合并 all-K、同步 row-job 消费和单元素 no-workspace；源码 SHA256 `e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea`。正式 submission `6ad2dff3193e507d8e1596b6` / 15/15 / score **14.64**，完整证据 `evidence/formal/fast-track-6ad2dff3/` 验证通过；低于 14.66，未晋升。未完成本地设备验证的风险见候选 `RESEARCH.md` 和 report 对应条目。

- 当前根及最高有效：`6ad2dbba193e507d8e11549f`，正式 15/15，score **14.66**；kernel SHA256 `b9a856aec216e11e8014a8808cc8f12be086a3dbf60831a3372c0d769a54a8a7`。完整恢复和 validate/decide 入口：`evidence/formal/fast-track-6ad2dbba/`；前根完整恢复：`evidence/formal/fast-track-6ad2d3be/source/`。
- 同轮独立正式结果 tile **14.55**、workspace **14.52**，完整 bundle `fast-track-6ad2da51/`、`fast-track-6ad2db06/`；未合并。候选入口 `optimization/candidates/aggressive-*/`，协议/队列说明 `optimization/AGGRESSIVE_COORDINATOR_20261017.md`。本轮未完成本地设备验证，风险及下一步见 report 最新条目。以下各“当前/最新”为历史时点。

## 通用 Fast Track 状态（2026-10-17，历史）

- 最新有效最佳：`6ad2d3be193e507d8e0a014d`，15/15，score **14.37**；根 kernel SHA256 `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`。实际 editable 文件为 kernel.asc；八文件服务端工程上下文与脱敏结果见 `evidence/formal/fast-track-6ad2d3be/`。前一最佳 14.34 完整恢复入口为 `evidence/formal/fast-track-6ad2d309/`。候选主机验证通过，未完成本地设备验证；逐点 TBest 对照为 `optimization/candidates/unit-token-scale-v2/COMPARISON.md`，后文各阶段“当前”属于历史状态。

- 服务端核查仍返回赛事 `ongoing=false`、`submit_enabled=false`，截止时间为 2026-10-17T10:00:00Z；该元数据与实际成功受理行为不一致，不能单独作为关闭证明。Shape、Cache、Scale Resident 及历史-mask+scale-resident 组合均已完成正式提交。
- 审计 staging：`/tmp/opencode/cannjudge-fast-track-audit-20261017/`。Shape、Cache、Scale Resident 的正式 8 文件工程均编译成功，优化逻辑均存在于对应上传的 `kernel.asc`；Scale Resident 使用独立 enabled staging 将默认宏设为 1。
- Shape 为 `6ad2c277193e507d8efb568a` / 15/15 / score 7.27，Cache 为 `6ad2c3a4193e507d8efc3550` / 15/15 / score 7.26，Scale Resident 为 `6ad2c647193e507d8efe5cf7` / 15/15 / score 7.29；新组合 `6ad2c82d193e507d8effe4e2` / 15/15 / score 11.76，已严格超过历史最佳 `6ad2872c193e507d8ed198c9` / 11.67。组合证据、hash、验证和风险见 `report.md`。

## Fast Track 正式结果（2026-10-17）

- Quant 候选已正式提交：submission `6ad2bff6193e507d8ef96ca5`，状态 `Pass`，15/15、全部 `precision_ratio=1`；同一 submission ID 的排行榜记录为 `rank=263`、score `7.26`。
- 实际 editable payload 只有 `kernel.asc`，SHA256 为 `cc7784d4546e15f879ac12583d6ef3bca058aa36bf8697f657a482e1a0d87bc4`。独立编译二进制 SHA256 为 `e481a0c1e6d1f103a3ea6ad5a60eadc944294fdf9bc47d56280c9cd7ee298da6`。
- 正式证据摘要和候选源码恢复副本：`evidence/formal/fast-track-6ad2bff6/`。该结果 score 低于历史有效最佳 `11.67`，未晋升；历史最佳 bundle 不变。
- Shape 正式证据及完整恢复源码：`evidence/formal/fast-track-6ad2c277/`；提交状态 `Pass`、15/15、排行榜 score `7.27`，与请求 submission ID 一致，未晋升。
- Cache 正式证据及完整恢复源码：`evidence/formal/fast-track-6ad2c3a4/`；提交状态 `Pass`、15/15、排行榜 score `7.26`，与请求 submission ID 一致，未晋升。
- Scale Resident 正式证据及完整恢复源码：`evidence/formal/fast-track-6ad2c647/`；提交状态 `Pass`、15/15、排行榜 score `7.29`，与请求 submission ID 一致，上传源码默认 `QUANT_SCALE_RESIDENT=1`，未晋升。
- 历史 mask + Scale Resident 组合正式证据及完整恢复源码：`evidence/formal/fast-track-6ad2c82/`；提交状态 `Pass`、15/15、排行榜 score `11.76`，与请求 submission ID 一致，上传源码 SHA256 `f8c53d3cfaf38bff415c4076d89426d551b04f8a988bff7ea9c989de3cad2163`，已按严格高于 11.67 的条件晋升为当前根实现。

## 当前状态

- 三 Agent 的六项配对 CAModel 任务已全部 passed，并经 `compare_scheduled_pair.py` 验收：quant cycles -43.521%、shape +0.031%、cache -0.526%，均为各自单 case 诊断；完整证据索引见 `optimization/MULTI_AGENT_INTEGRATION.md` 与 `report.md`。
- 后续核查发现 `evidence/formal/fast-track-6ad2d309/`（15/15、score 14.34）离线 valid、相对 14.02 eligible。但根源码在核查期间被并发研究修改为 `782b573...`，本会话未覆盖或晋升；下列根 hash/14.02 状态为此前时点记录，最新工作根与正式最佳不得混同。详见 `report.md` 的并发工作区保护条目。
- 最新正式有效结果为 submission `6ad2d3be193e507d8e0a014d`，15/15、score **14.37**；`evidence/formal/fast-track-6ad2d3be/` validate/decide 通过，完整上传文件 hash 与当前工作树一致，当前根 `kernel.asc` 为 `782b573...`。14.34 bundle 保留为前一候选，不覆盖最新结果。

- 14.02 基线派生候选 `optimization/candidates/row-parallel-all-16/` 已正式晋升：submission `6ad2d309193e507d8e0959e9`、15/15、同提交 score **14.34**，正式证据 `evidence/formal/fast-track-6ad2d309/`。kernel SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`；本地设备 smoke 因 aclInit ret=500000 未完成。错误编码的 host-only strict 记录已隔离，job `1792201151308-7d43d82ba8` 标记 invalid_validation、队列 halted，禁止用其提交；审计与风险见 `report.md`。

- 当前最高有效版本：`6ad2d309193e507d8e0959e9`，Pass 15/15，score **14.34**；`row-parallel-all-16` 候选已晋升，证据 `evidence/formal/fast-track-6ad2d309/`，源码/研究记录 `optimization/candidates/row-parallel-all-16/`，晋升前根快照 `optimization/snapshots/pre-row-parallel-all-16/kernel.asc`。未完成本地设备验证；继承 ownership/tiler、同步和大 K 数值风险，详见 `report.md`。

- CUDA direct-cast 候选源码 SHA256 `12ea67588b185772e47cf4b35d3a551c640f29158c4b1e743c75f538d4cae818`；编译、主机检查和两个严格 CAModel smoke 通过，完整设备回归未运行。Fast Track job `1792199099715-f519856f91` 在显式会话重试后正式提交为 `6ad2cdc8193e507d8e04ca9c`，15/15、同提交 score 11.63，未晋升。恢复源码和脱敏摘要：`evidence/formal/fast-track/6ad2cdc8193e507d8e04ca9c/`；通用校验器与该归档 schema 不兼容，详见 `report.md`。

- Fast Track 已接入新启动 Coordinator 的默认正式评测队列：`optimization/fast_track.py`、`optimization/FAST_TRACK.md`、`optimization/multi_agent_worker.py`。Agent 显式 enroll 后由 Coordinator 串行提交、按 submission ID 对账并归档脱敏摘要；CLI 仅对明确 HTTP 429 等待提示自动重试未受理 POST，其他异常仍 fail-closed。新增限流测试及既有 Fast Track 回归通过；已有运行进程未重启，未安装常驻服务。

- 双 Worker host-only 并发兼容性入口：`optimization/experiment_dual_worker.py`；同队列/跨队列两个场景各 12 项任务通过且无执行重叠，证据 `/tmp/opencode/dual-worker-host-v1rlwl6b/summary.json`。未运行真实 CAModel 双实例；详见 `report.md`。

- 三 Agent 上线集成入口与交接记录：`optimization/MULTI_AGENT_INTEGRATION.md`；共同研究基线 `5574de4`，统一 Worker 驱动 `optimization/multi_agent_worker.py`。三个 host-only 任务通过，quant 候选经共享队列完成一个严格 INT32 CAModel smoke；cache/shape 的后续正式 staging 已完成并提交，CAModel 配对结果仍按队列状态记录。本轮 Shape/Cache 有新官方 score，但均未晋升。
- 后续三路 baseline/candidate 均已独立编译并提交配对任务，结果待完成；cache/shape 的“尚无二进制”仅适用于首次交接。配对终态/严格正确性/共同 fingerprint 核验入口为 `optimization/compare_scheduled_pair.py`，任务与构建证据索引见 `report.md` 及各 worktree 候选的 `RESEARCH.md`。

- 当前工作实现为根 `kernel.asc`，SHA256 为
`0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`。
- `optimization/candidates/row-parallel-16/` 已由首次 HTTP 429 后的明确等待重试获得正式 submission `6ad2cf40193e507d8e061327`、score 14.02 并晋升；分析与逐点对照见 `optimization/TBEST_ANALYSIS_20261017.md`，完整证据见 `evidence/formal/fast-track-6ad2cf40/`。
- `optimization/candidates/unit-token-scale/kernel.asc` 为跳过 unit token scale 乘法的
  未编译、未正式验证候选，未晋升；优化前快照位于
   `optimization/snapshots/pre-unit-token-scale/kernel.asc`；根现已晋升正式 mask+scale-resident 组合，晋升前根备份为 `optimization/snapshots/pre-historical-mask-scale-resident/kernel.asc`。
- 当前根默认 `QUANT_MASK_FAST_PATH=1` 且 `QUANT_SCALE_RESIDENT=1`（仅在 `N <= VECTOR_TILE_N` 时启用 scale residency）；`K >= 65536` 时使用 FP32 Matmul 路径。
- `op/kernel_v3.asc` 为冻结快照，SHA256 为
  `64c6384d6f72449ca59a13cfa076b6b93dd5ae7ea548b7f39f9f32732e220220`；当前根包含新增 scale residency，不与 v3 逐字相同。
- 已复核的历史正式有效提交及 score 记录在 `report.md`；原始结果位于
  `/tmp/opencode/kernel-existing-submission-result.json`，排行快照位于
  `/tmp/opencode/cannjudge-ranking-team-file.json`。这些文件不属于仓库版本内容。
- 本地 `optimization/test_points.json` 是自建回归，不是正式 15 个测试点；CAModel 结果不替代正式 score。
- `optimization/int32_golden.py` 是严格 INT32 主机参考与边界回归入口，覆盖 K=65536、K=131072、INT32 signed boundary、极值 INT8、scale 下溢/负 scale 和 half-even；它不是设备或正式评分结果。
- `optimization/camodel_scheduler.py` 与 `camodel_resource.py` 提供非阻塞队列、不可变候选快照、独立结果目录和主机级单 CAModel lease；现支持显式 case 任务优先级、`--cases-json` 批量拆分、以及只在 case 边界生效的协作式 pause/yield；`optimization/test_camodel_scheduler.py` 覆盖跨队列互斥、状态结束、异常恢复、快照隔离和优先级让出。
- `optimization/accept_scheduler.py` 是显式 opt-in 的真实 Case 1 调度器验收脚本；最近一次完整验收记录位于 `/tmp/opencode/scheduler-acceptance-ssu3h5ye/acceptance.json`，通过单 Worker、资源竞争、排队快照和 Worker 异常退出场景。
- `evidence/formal/` 保存不含原始回包的正式结果元数据、提交文件 hash 和历史提交源码恢复副本；离线校验入口为 `evidence/formal_evidence.py`，原始结果仍位于受保护的仓库外路径，详见 `report.md`。

## 1. 从哪里开始看

1. **题目与约束**：[ques/quantmatmulreluquant.md](ques/quantmatmulreluquant.md)。
2. **当前开发入口**：[kernel.asc](kernel.asc)，由根 `main.asc` 和实验程序共同引用。
3. **保留版本**：`op/` 下的三个 kernel，不覆盖、不当作临时实验文件使用。
4. **现有评测与风险**：先看 `ev/`，再看 `optimization/` 中的历史实验。
5. **正式结果与恢复**：先看 `evidence/formal/README.md` 和 `report.md`，再使用只读的 `evidence/formal_evidence.py`。
6. **复现测试**：使用 `optimization/benchmark.py`；单点示例入口为根 `main.asc`。
7. **外部实现参考**：看 `reference/README.md`，再按 AscendC → DynamicQuant → CUDA epilogue 顺序阅读。

### 历史状态说明（以下为先前 RNE-distance 阶段，当前身份见上文）

- 当时根 `kernel.asc` 为 RNE-distance mask 正式 payload，保留 `QUANT_MASK_FAST_PATH=1` 与 `QUANT_SCALE_RESIDENT=1`；SHA256 为 `007b6fb9ba6f55d5033f644fcc6cc6c975666ea9dd7d1c4d08bca9e38b674aab`，与 `evidence/formal/fast-track-6ad2cb6b/` 一致。晋升前 11.76 根快照为 `optimization/snapshots/pre-rint-distance-mask/kernel.asc`。
- `op/kernel_v3.asc` 是开启 boundary-mask 快路径时的冻结快照；用户外部评测曾 15/15 通过，但这不是所有 FP32 输入的正确性证明。
- `op/kernel.asc` 是历史对照基线，`op/kernel_v2.asc` 是早期候选快照，均保留不动。
- `bench_vector` 仅消融量化精确校正；**仍包含矩阵乘等整个算子阶段**，不是已完成的独立纯 Vector 微基准，也不是可提交的正确实现。
- `optimization/vector_error_distribution.py` 是宿主误差模型，不是设备指令误差分布或设备误差上界证明。
- 历史安全回归记录在 `report.md` 和 `optimization/safe_regression.log`；这不是当前根与正式提交一致性的证明，也不是官方 15/15 或 score 证据。
- `reference/` 保存公开源码/文档入口和分析，不保存未经核对的第三方代码副本；CUDA 资料可用于算法、数值处理和结构对照，但不能未经适配当作 AscendC 实现。

## 2. 根目录：实现与单点执行

| 文件/目录 | 用途 | 备注 |
|---|---|---|
| `kernel.asc` | 当前 AscendC kernel、tiling、workspace 和启动实现 | 主要优化对象；含 Cube/Vector 阶段和 exact 量化逻辑 |
| `main.asc` | 本地单点运行程序 | 引入根 kernel；读取输入、分配设备内存、启动并保存结果 |
| `CMakeLists.txt` | 单点程序构建配置 | 生成 `quant_matmul_relu_quant_custom`，默认架构 `dav-2201` |
| `data_utils.h` | 二进制文件读写辅助函数 | 本地运行基础设施 |
| `run.sh` | 一键构建、生成 case0、运行和校验 | **会删除并重建整个根 `build/`**；已有结果需先保留；本次不执行它 |
| `build/` | 根工程生成产物 | 可执行文件、CMake 缓存、对象文件、`input/`、`output/`；不是源码版本依据 |
| `roadmap.md` | 当前导航、版本状态、复现入口与待办 | 本文件 |
| `reference/` | CANN GroupedMatmul/DynamicQuant、FFNQuant、CUTLASS、vLLM、TensorRT-LLM、Triton-Ascend 等参考入口与适用性分析 | 详见 `reference/README.md` |
| `gitlabcann/` | CANNJudge 在线提交、结果查询和排行榜指标工具 | 实际是 CANNJudge API 客户端，不是 GitLab OAuth 客户端；详见下文 |

## 2.1 `gitlabcann/`：CANNJudge 提交工具

| 文件 | 用途 | 备注 |
|---|---|---|
| `gitlabcann/README.md` | 提交工具的登录、提交、结果查询和排行榜查询说明 | 默认对应本题赛事与题目 |
| `gitlabcann/cannjudge_cli.py` | CANNJudge 命令行客户端 | 支持登录、提交工程、轮询结果、查询已有提交及读取 `rank`/`score` |
| `gitlabcann/userid.txt` | 本地未跟踪的默认 CANNJudge 用户 ID | 提交和排行榜命令自动读取；可用 `--user-id` 覆盖；不属于版本化输入 |
| `team.txt` | 默认排行榜搜索队伍名称 | 当前值为 `西西里 的队伍`；排行榜命令可用 `--query` 覆盖 |
| `gitlabcann/cookie` | 登录会话 Cookie | 敏感凭证，不应分享或提交到版本库 |
| `gitlabcann/__pycache__/` | Python 自动缓存 | 非源码 |

注意：该工具向 CANNJudge 提交，不是 GitLab OAuth 客户端；实际上传文件以服务端
题目模板中的可编辑文件为准。已复核的历史提交文件清单、hash、结果和排行榜快照见
`report.md`；Cookie 仍为敏感凭证。

## 3. `ques/`：题目原始资料

| 文件 | 用途 |
|---|---|
| `ques/README.md` | 来源、文件说明和题目关键元数据 |
| `ques/quantmatmulreluquant.md` | 公开 API 中 `desc` 字段的可读题面，附来源信息 |
| `ques/quantmatmulreluquant.json` | 公开 API 完整原始响应；保留版本、CANN 版本、测试点 ID 等 |

来源：<https://cannjudge.cn/public/op_challenge_hangxia_prelim/quantmatmulreluquant>。

题目要求 `x1(M,K)`、`x2(N,K)`、按顺序执行 INT32 matmul → FP32 cast → 两次 scale 乘法 → ReLU → 行最大值/127 → 除法 → rint（就近偶数）→ clamp。零行 `yScale=1`、`y=0`。

**已确认的区别与待核对事项：**

- 题目元数据标注 CANN **9.0.0**，本地实验使用 **9.1.0**；接口与精度结论不能无条件跨版本沿用。
- 题面 CPU 参考使用 **INT32 matmul**；历史 `scripts/QuantMatmulReluQuant.py` 和旧 benchmark 记录曾使用 FP32 matmul，当前 `optimization/benchmark.py` 已输出严格 INT32 主结果和 FP32 对照。大 K、累加溢出/转换边界仍须结合设备结果独立核对。
- 题面没有给出 15 个正式测试点的具体形状；API 返回的测试点 ID 不等于输入数据。`optimization/test_points.json` 的 15 点是本地自建回归，不能与正式编号对应。
- 题面性能章节描述含 H2D/Kernel/D2H 的端到端时间；本地记录的是 CAModel task cycles。正式评测实际计时范围仍需核对，不能直接互换。
- 题面精度章节未单独说明 INT8 容差；本工程继续采用 **INT8 完全一致**、`yScale` 既有浮点容差作为保守验收口径。

## 4. `op/`：冻结版本

| 文件 | 身份 | 实验 variant |
|---|---|---|
| `op/kernel.asc` | 历史 prior 基线 | `prior` |
| `op/kernel_v2.asc` | v2 优化快照 | `v2` |
| `op/kernel_v3.asc` | v3 mask 候选冻结快照 | `v3` |

冻结 SHA256：

```text
op/kernel.asc     1b7de3e2dc9920cb2350126a356e53f9b4986a095af4d212e28c2b8cb718dfe3
op/kernel_v2.asc  3d0e63cd4a9ac3023474ac05800783ed49b4ee38a00270da4c72d029210b63ad
op/kernel_v3.asc  64c6384d6f72449ca59a13cfa076b6b93dd5ae7ea548b7f39f9f32732e220220
```

## 5. `scripts/`：原有单点数据与结果检查

| 文件 | 用途 |
|---|---|
| `scripts/QuantMatmulReluQuant.py` | 本地 NumPy golden `impl` 和相关用例定义；注意上文 FP32/INT32 matmul 差异 |
| `scripts/gen_data.py` | 为原有 case0 生成 `input/` 和 golden 二进制文件 |
| `scripts/verify_result.py` | 校验 case0 输出；INT8 严格相等，FP32 按配置容差检查 |
| `scripts/__pycache__/` | Python 自动缓存，不是测试结果 |

## 6. `ev/`：评测结论与正确性门槛

| 文件 | 用途 |
|---|---|
| `ev/V3_EVALUATION.md` | 用户提供的外部 15 点 v3/最优耗时、性能差距和下一步分析；原来位于 `optimization/` |
| `ev/ASCENDC_MASK_SELECT.md` | AscendC Compare/Compares/Select 接口核查；mask 布局与压缩能力限制 |
| `ev/QUANT_ERROR_BOUND.md` | 条件性误差界、半整数 fallback 判定与设备精度证明缺口；解释关闭默认 mask 快路径的原因 |

## 7. `optimization/`：可复现实验

### 代码和设计文档

| 文件 | 用途 |
|---|---|
| `optimization/README.md` | 优化设计、复现方式和历史性能数据；部分“当前快照”描述已是历史状态，以本 roadmap 为导航 |
| `optimization/STRUCTURAL_EXPERIMENTS.md` | mask、vector-only、两 tile cache、N tile=128 的实验与限制 |
| `optimization/CUDA_REFERENCE.md` | CUDA/CUTLASS 结构参考；不用于推定 AscendC 舍入/scale 语义 |
| `optimization/CMakeLists.txt` | 构建多个对照 variant |
| `optimization/bench.asc` | 可传入 M/N/K 的统一运行器，通过编译宏选择 kernel |
| `optimization/benchmark.py` | 固定种子生成输入/golden、串行运行 CAModel、比较输出、记录 cycles 和二进制 hash |
| `optimization/camodel_scheduler.py` | 多 Agent 实验队列；默认单 Worker、主机级 CAModel 互斥、不可变任务快照、case 优先级和协作式边界让出 |
| `optimization/camodel_resource.py` | 主机级 CAModel lease 及遗留未托管模型进程 fail-closed 检查 |
| `optimization/test_camodel_scheduler.py` | 调度器轻量并发/生命周期测试，不启动真实 CAModel |
| `optimization/accept_scheduler.py` | 显式 `--real-camodel` 的真实 Case 1 调度器验收；仅使用已有二进制和新隔离目录 |
| `optimization/test_points.json` | 本地 15 点及 profile 说明；runner 的 `SUITE` 另有一份定义，修改用例时需同步 |
| `optimization/check_quant.py` | 提取根 kernel exact helper，在宿主 C++ 上测试随机 hint、半整数边界和 IEEE mask 模型 |
| `optimization/int32_golden.py` | 严格 INT32 累加/显式 int32 wrap 的主机 golden 与大 K、scale、舍入边界回归 |
| `optimization/vector_error_distribution.py` | 假设 reciprocal 误差预算的宿主扰动实验；不能代替设备 reciprocal 精度保证 |
| `optimization/baseline/kernel.asc` | 更早的原始源码对照，不是 `op/kernel.asc` |
| `optimization/candidates/`、`optimization/snapshots/` | 未晋升候选和修改前快照；当前为 `unit-token-scale/kernel.asc` 与 `pre-unit-token-scale/kernel.asc` |

### variant 对照

| variant / 可执行文件 | 对应实现 |
|---|---|
| `baseline` / `bench_baseline` | `optimization/baseline/kernel.asc` |
| `prior` / `bench_prior` | `op/kernel.asc` |
| `v2` / `bench_v2` | `op/kernel_v2.asc` |
| `v3` / `bench_v3` | `op/kernel_v3.asc` |
| `optimized` / `bench_optimized` | 引用当前根 `kernel.asc`，默认 mask 与 scale residency 开启；既有二进制必须重编译，不能继承新源码身份 |
| `vector` / `bench_vector` | 根 kernel + `QUANT_VECTOR_ONLY=1`，仅性能消融 |
| `cache` / `bench_cache` | 根 kernel + 两 tile activation cache 实验 |
| `tile128` / `bench_tile128` | 根 kernel + Cube base N=128 实验 |

### 日志与生成产物

| 路径/命名 | 用途 |
|---|---|
| `optimization/safe_regression.log` | 关闭默认 mask 快路径后的本轮 prior/optimized 回归输出 |
| `optimization/case15_long.log` | 历史 tiny-scale 点长时仿真结果 |
| `optimization/boundary_device.log` | 历史半整数边界设备仿真；scale=1 不覆盖非精确倒数 |
| `optimization/cache_tile.log` | 两 tile cache 与 N tile=128 对照 |
| `optimization/suite*.log` | 历史批量/边界用例的输出；不能直接当作当前二进制的结果 |
| `optimization/benchmark*.log`、`run*.log` | 不同阶段的历史运行记录；需结合输入、variant、hash 解读 |
| `optimization/configure*.log`、`build*.log` | CMake 配置/编译记录；`configure_final.log` 包含一次未 source 环境的失败，`configure_safe.log` / `build_safe.log` 是后续构建记录 |
| `optimization/build/` | 当前实验可执行文件和编译缓存 |
| `optimization/results/<case或shape_profile>/<variant>/` | 每次实验输入、golden、实际输出、`result.json`、`run.log`、CAModel `logs/`；超时另存 `failure.json` |
| `optimization/baseline/` 中的二进制与 dump | 早期基线运行遗留产物；区别于同目录的源码 |
| `optimization/__pycache__/` | Python 缓存 |

`result.json` 中关注 `int32_mismatches`、`int32_scale_ok`、`fp32_mismatches`、`fp32_scale_ok`、`binary_sha256`、`task_cycles` 和完整 `fingerprint`。`BENCHMARK_RESULTS_ROOT` 可将本次输出定向到隔离目录。宿主仿真墙钟时间不代表 NPU 延迟。

## 8. 常用复现入口

从当前根目录执行，先加载本地 CANN/CAModel 环境：

```bash
source ../env.sh Ascend910B1
cmake -S optimization -B optimization/build
cmake --build optimization/build -j4
python3 optimization/check_quant.py
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --case-ids 1 5 6 --variants prior optimized --timeout 1800
```

完整自建 suite：

```bash
OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --suite --variants prior optimized --timeout 1800
```

CAModel 回归应串行执行，避免与正在运行的任务共用相同结果目录。`--resume` 仅在完整 fingerprint 匹配时复用结果；fingerprint 覆盖输入、双 golden、variant 源码、benchmark/golden 脚本、测试点文件、二进制和关键环境变量。

## 9. `evidence/`：正式结果证据与恢复

`evidence/` 是正式评测结果的可版本化、脱敏证据层，不保存 Cookie、会话令牌或原始 API 回包。正式结果的来源、score 和当前根差异见 `report.md`；仓库内校验器只检查元数据、文件集合和 hash 的一致性。

| 路径 | 用途 | 备注 |
|---|---|---|
| `evidence/formal/README.md` | 证据规范和离线命令 | 包含权限、脱敏和恢复边界 |
| `evidence/formal/manifest.txt` | 历史提交摘要索引 | 包含提交、15/15、score、来源路径和 SHA256 |
| `evidence/formal/submission-files.sha256` | 实际 editable 文件的 hash 清单 | 当前历史提交为 8 个文件 |
| `evidence/formal/historical-6ad2872c/` | 历史提交 bundle | `evidence.json` 与 8 个可恢复源码文件 |
| `evidence/formal_evidence.py` | 离线 `recover`、`validate`、`decide` 入口 | `recover` 创建新 bundle；`decide` 只输出资格，不修改工作树 |
| `evidence/test_formal_evidence.py` | 离线校验单测 | 覆盖字段、15/15、score 归属及源码 hash 等拒绝条件 |

从根目录执行历史 bundle 校验：

```bash
python3 evidence/formal_evidence.py validate evidence/formal/historical-6ad2872c
python3 -m unittest evidence.test_formal_evidence
```

`recover` 只应针对已核对的受保护快照运行；`decide <candidate> --best <bundle>` 要求相同 scoring context 且 score 严格更高。正式晋升仍须另外确认实际上传 payload、submission ID、服务端 15/15 和同一提交的官方 score。
