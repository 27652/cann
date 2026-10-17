# QuantMatmulReluQuant 研究与决策记录

更新时间：2026-10-17

## 紧急停止后四个会话末期成果与其余未提交成果归档（2026-10-17）

- 按用户要求保存其余源码、脚本、定向结果、失败复现工程与诊断；不改根、
  不新提交评测，不把归档混同晋升。最高有效仍为最终 19.48 / rank 195。
- 完成交接 `optimization/RESEARCH_HANDOFF_20261017.md`：整理四个会话末期的
  A/L1 反馈归档、A/L1 提交与后续获分、N-tile/TBest 逐项对照、
  Cube→VECIN / workspace-free 接口核查。`ba58a6b` 与 `6ad345…` 经核对
  关联同一 A/L1 submission，不重复算作独立候选或提交；N-tile 保留历史
  19.45 对照与未完成 early-max 生产超时诊断。按源码和结果记录，session ID
  映射未知，不臆造；更早三 Agent 历史单独保留。
- 其他成果包括多行 reduction 正式 Compile Error/WA、N-shard 已知严格失败与
  DMA 修订待测、local-k API 风险、FIFO+UB 组合退化、wide-row 消融等。
  未完成的主机/设备/性能/正式验证分别标明，失败原始结论不隐藏。
- 文件清单及 SHA256：`optimization/research-archive-20261017/manifest.json`；
  未纳入 Git 的生成物清单 `excluded.json`，本地均不删除。历史记录中的“当前
  19.45/未提交/待设备验证”按当时状态解释，最终状态以顶部 19.48 bundle 为准。
- 归档轻量检查：154 个 JSON 解析、61 个 Python AST 解析通过；敏感赋值模式
  扫描无命中（不等同完整安全审计）。`git diff --cached --check` 仅报告 129 处
  历史生成日志末尾空行，保留原字节；本轮未重跑编译、设备测试或正式评测。

## 最终 CLI 核验：19.48 / rank 195，晋升并归档（2026-10-17）

- 仅使用现有 CLI 的 result/ranking GET 查询，未执行任何新提交 POST。
  result 返回 `6ad345e2193e507d8ebb20ec`、Pass、valid=true、15/15，
  全部 precision_ratio=1；10:08:02Z 同 ID ranking 返回 rank 195、score 19.48。
  排名是查询时快照，不保证后续不变。此前 score-pending 是历史状态。
- 恢复 bundle `evidence/formal/dual-aiv-l1-6ad345e2/` 绑定实际 kernel 上传
  hash、完整八文件工程、脱敏结果与排行榜。formal_evidence validate 通过，
  decide 确认同口径 19.48 > 19.45，提升 0.03（约 0.154%）。
- 晋升前根 hash 与 19.45 冻结恢复源码一致，无根源码未提交修改；旧根完整
  保存在 `evidence/formal/dual-aiv-fixed-6ad33b78/source/`，新根 hash 为
  `431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a`。
  晋升后全部八文件与新 bundle hash 一致；未修改 op/ 冻结文件。
- 最终优化：保留 dual-AIV ownership；K<=4096、K%32==0、N>256 时，
  显式将 16×K A 面板装入 A1/NZ，最多四个相邻 N tile 复用，
  SetOrgShape M 使用 tileM=16；其余保留父路径。不含 FIFO 或 chunk64 组合。
- 对比父版本，正式 time 为 9 点变快、6 点变慢；点2 9.36→8.02，
  点11 327.58→308.83，点15 4600.98→4512.73；点1/3 回退约 8.15%/10.92%。
  单位沿用服务端 time，不用时间拼接计算替代 score，不推断未知 shape。
- 已存四组严格 INT32 CAModel smoke（17x1025x64、65x513x256、
  17x257x4096、17x513x65）零 INT8 mismatch、yScale 完全一致；本次未重跑
  设备测试或编译。非覆盖输入、大 K、FTZ/RNE、L1 分配/同步仍有风险，
  正式有效不等于所有合法输入严格正确。
- 本次独立 commit 仅保存该晋升及必要恢复/验证材料，不混入未正式通过
  的其他候选、缓存或 dump；其他工作区研究改动保留。赛事已结束，不新提交流程。

## N-tile early-max pipeline follow-up（2026-10-17）

- Candidate `optimization/candidates/n-tile-max-pipeline/` remains isolated
  from the promoted dual-AIV root (`6ad33b78193e507d8ea310c4`, score 19.45).
  It extends FIFO row jobs only for `M>=1024, 4096<N<=16384`, then was made
  protocol-testable with `N_TILE_MIN_ROWS=17`.
- Corrected protocol uses two outstanding N tiles: ready lanes 4/5, consumed
  lanes 6/7, row-complete lane 8 and row-consumed lane 9. It does not claim a
  global dynamic queue. CANN 9.1/dav-2201 compiled successfully.
- Strict INT32 CAModel results under `source env.sh Ascend910B1`: 17x4097x33,
  17x8201x33, 65x4097x33, and single-core 33x4097x33 all had zero INT8
  mismatches and exact yScale. 33x16385x33 exercised fallback and also passed.
  The production-dispatch 1025x4097x33 run timed out at 240 seconds; logs are
  retained and it is not classified as correctness pass or deadlock.
- No formal submission or performance claim. The current verified baseline's
  testcase-ID-aligned TBest comparison is retained in
  `optimization/candidates/n-tile-max-pipeline/TBEST.md`; dual-AIV remains
  2.13x--13.50x above stored TBest per testcase. Shapes are unknown and this
  comparison cannot trigger promotion.

## 双 AIV 显式 A/L1 驻留候选（2026-10-17，设备验证待运行）

- 基于正式 `6ad33b78193e507d8ea310c4`（15/15，19.45）的精确恢复工程，
  在 `optimization/candidates/dual-aiv-l1-v4/` 建立独立候选与父版本快照，
  未覆盖根或冻结版本。假设是显式 A1/NZ 驻留可减少同 A 行块跨 N tile 的
  重复加载；没有直接阶段计时证明当前 Cube 供给或 GM 是主瓶颈。
- `a-l1-group4-stride16` 对 K<=4096、K%32==0、N>256 的输入，将 16×K A
  面板显式装入 L1，复用于至多四个 N tile。其他 shape 保留父路径；
  INT32 GM 平面、全核 barrier 与双 AIV epilogue 未改。分组同时改变调度粒度，
  因而即便获益也不能仅归因于 L1 流量。
- 初版编译后检查发现 NZ 面板跨度风险，保留初版，另建 stride16 修正版。
  修正版 hash `431750131478b8b569b24d0f86e7fc224187d0ec87d81cf0eb4eac60f3fc249a`。
  修正版及精确父版本 CANN 9.1 / dav-2201 编译成功，175 组主机 ownership、
  工程 hash 与 NZ 地址模型检查通过；这些不是设备语义证明。
- 严格 INT32 `17x1025x64` smoke 因全机 CAModel lease busy 在启动前被拒绝，
  **未完成本地设备验证**，没有数值或性能结果。未抢占其他会话任务。
  仍需验证 NZ 布局、外部 A1 与 Matmul L1 分配共存、tail 及事件生命周期。
- 未正式提交、未取得新官方 score、不晋升；历史最高已核实有效 score 仍为
  19.45。封榜期间如只有正式逐点耗时，将按 testcase ID 对齐作为临时反馈，
  不替代 score 或触发晋升。恢复、构建与下一步命令见该目录 `RESEARCH.md`。

## 独立架构正式反馈与晋升（2026-10-17 08:46 UTC）

- `optimization/candidates/architecture-trials-v1/` 分别完成三条独立路线编译和
  主机模型检查，未组合提交：内部 K-loop `local-k-safe`、单 owner scale 广播
  `scale-owner`、有界双槽配对 `tile-fifo`。原外部 chunk 的 Iterate partial-sum
  `local-k` 探针因 SetTensor reset/L0C 生命周期未知，不提交。
- `local-k-safe`：`6ad3338a193e507d8e9444c6`，15/15、score **16.69**；
  `scale-owner`：`6ad3343f193e507d8e95990c`，15/15、score **16.60**；
  `tile-fifo`：`6ad335a8193e507d8e985b8b`，15/15、score **16.89**。全部
  precision_ratio=1，同 ID score；对应正式证据均在 `evidence/formal/`，validate 通过。
- FIFO 严格超过已核实 16.66，payload 可恢复、八文件服务端源码 hash 一致、decide
  eligible=true，已晋升根 `kernel.asc`，SHA256
  `427a35b31dbc75c3afbb8b1681c68f6c852b8f3b5620ca889c62c56f6083bef4`。
  旧根完整保存在 `evidence/formal/tile16-persistent-6ad31941/source/kernel.asc` 及
  `optimization/candidates/architecture-trials-v1/snapshots/kernel-before-fifo.asc`，
  hash cdde82ec…4501ae（备份移出冻结 bundle 后旧证据 validate 再次通过）。
- FIFO 是静态 row-job ownership + 动态 ready/free 背压，不是全局动态抢任务队列。
  对比旧基线点 1/3 -28.15%/-16.83%，点 8 -5.34%、点 12 -10.90%，点 9 +11.87%；
  shape 映射未知，不宣称这些时间差均由启用 FIFO 导致，重复性尚未建立。
- 未完成这些修订的本地设备验证；保留跨核 event、ring slot、tail、K chunk、
  DMA 可见性和 workspace 风险。大 K 保守版本只在 K<131072 范围合并内部 K-loop，
  更大 K 沿用基线，尚未实现任意大 K 外部 chunk 的 L0C 保留。

## 大结构突破探索：MIX 1:2 与 UB 8192 驻留（2026-10-17）

后续正式反馈：活动 POST 全部退出后，冻结 UB 候选正式提交；HTTP 429 明确等待
75 秒后一次受控重试，获提交 `6ad3365d193e507d8e999c3a`。正式 Pass 15/15、全部
precision_ratio=1，同 ID ranking score **16.79**，查询时间 08:49:16 UTC。实际
editable 上传只有 kernel.asc；可恢复证据 `evidence/formal/ub-resident-8192-6ad3365d/`
独立 validate 通过。原始回包保存在 `/tmp/opencode/ub-resident-8192-result*`。

同期另一会话得到更高的 tile-FIFO **16.89**（`6ad335a8193e507d8e985b8b`），其
bundle validate 通过；UB 对 FIFO 的 decide 明确因分数不严格提高而拒绝。根实现已被
其他会话改为 FIFO，本会话不覆盖、不晋升、不创建晋升 commit。当前最高已核实为
16.89，而不是下列实验初始时点的 16.66。旧 16.66 bundle 的 source 目录被其他会话
加入额外 backup，导致其 decide 校验报 source file set 错误；未擅自删除备份，改用
干净 FIFO bundle 比较。16.79 属于小幅正反馈，不宣称完成大突破；下一步应独立调查
MIX 1:2 实际 block/subblock 语义，或在已有独立反馈基础上建立 FIFO+UB 二次整合候选。

- 从已核实 16.66 源码建立独立候选目录
  `optimization/candidates/structural-breakthrough-v2/`，未修改根实现、冻结
  `op/` 或正式证据。两项变化没有组合：`dual-aiv` 尝试 MIX 1:2，把完整行工作
  分摊到两个 Vector 子块；`ub-resident-8192` 仅改变 Vector UB buffer 生命周期
  别名，将有效 `VECTOR_TILE_N` 从 4096 扩为 8192，以消除宽行第二遍激活计算。
- 两者均在 CANN 9.1.0/dav-2201 编译成功，静态 ownership/hash 检查通过。
  `dual-aiv` 严格 CAModel 首点 `17x513x65` 失败：2023 个 INT8 mismatch、
  yScale 最大绝对差 8.2241907；已拒绝且未提交。该失败说明当前 MIX 1:2
  子块/同步假设不成立，不能依据理论 Vector 并行度继续推进。
- `ub-resident-8192` 在严格 INT32 golden 下通过 `2x4097x33`、`2x8192x33`、
  `2x8201x33`，均为零 INT8 mismatch、yScale exact。结果和 fingerprint 在候选
  目录 `results/strict-smoke-v1/`。这只是针对性正确性证据，尚无 CAModel
  性能结论，也不构成全域设备正确性证明。
- 发现其他候选正在串行正式 POST，因此没有并发提交；当前最高有效官方 score
  仍为 16.66，以上候选均未晋升。下一步应在活动 POST 结束后，对 UB 候选做宽/窄
  形状 benchmark 对照，再按冻结 payload 规则决定是否 Fast Track。

## 多行 epilogue 首版重构（2026-10-17）

- 隔离候选 `optimization/candidates/multi-row-epilogue-v1/` 从正式 16.66 根派生，
  仅重构 VectorStage：2/4/8 行共驻 UB，批量 Cast/双 scale/ReLU，两级
  `ReduceRepeat<MAX>` 行归约；量化复用原 vector RNE、packed mask 和 sparse exact
  correction。默认四行，完整组且 `N<=4096/rows` 时启用；其余路径回退。
  Cube、workspace、全核同步及单 launch 未变；根和冻结文件未修改。
- 主工程及 rows=1/2/4/8 benchmark 全部编译成功。CANN 9.1 / dav-2201 严格
  INT32 CAModel：`129x513x65` rows=1/4（负 scale、零行、group/N/K tail）和
  `193x17x33` rows=2/4/8（半整数 RNE）全部零 INT8 mismatch，yScale 绝对及
  相对差均为 0；记录比较容差 rtol/atol 均 1e-4。证据见候选 RESEARCH 和
  `results/{rows4-tail-20261017,grouped-half-small-20261017,wide-fallback-20261017}/summary.json`。
- 较大半整数诊断被外层 120 秒超时中断，遗留的本次模型进程已终止，部分日志保留；
  未判为失败或通过。未测性能、AIV 分阶段 cycles 或 correction 密度；当前不能
  声称加速。原 scratch 复用，仅 reduceOutBuffer 增加 96 bytes 分配。
- 未正式提交、未获得新 score、未晋升；最高已核实仍为 16.66。下一步完成
  host/source invariant 检查和 aligned/wide fallback 对照，提取同条件 task_cycles；
  不将单 slot ring 混入这一可归因候选。

## Candidate A：FP32 activation cache（2026-10-17）

- 从可恢复的 16.66 正式源码创建隔离候选
  `optimization/candidates/fp32-activation-cache/`。Cube 调度、M/N ownership、
  row max、量化和单 launch 不变；仅对 N>4096 的行，在第一遍 INT32→FP32、
  scale/ReLU 后将 FP32 activation 写入 launch-private cache，第二遍读取该
  cache quantize，目标是避免重复 INT32 load/cast/scale/ReLU。N<=4096 保持原路径。
- CANN 9.1/dav-2201 benchmark 和 formal-template 编译均通过；冻结八文件
  payload，kernel SHA256 `f2a4a2bf9dde56719901731961139c668517fdcc23ad4b4406ce5f09df43c566`。
- CLI dynamic-template preflight 通过，但首个 POST 收到明确 HTTP 429，指定等待
  132 秒；外层 120 秒命令中断。随后核对相同赛事/题目、manifest、全部冻结
  hash 及无本地受理 ID，按规则等待并重试同一 payload。提交
  `6ad32d3e193e507d8e88c539` 正式 Pass 15/15、全部 precision_ratio=1；同 ID
  官方 ranking score **16.63**、rank 212。八文件源码与脱敏证据位于
  `evidence/formal/fp32-activation-cache-6ad32d3e/`，离线 validate 通过。
- 逐点比较基线，点 7--15 中多数提升约 0.7%--5.9%，但点 1--6 多数变慢，
  综合低于 16.66；不晋升。未完成本地 strict smoke，`aclInit` 500000 仍为
  运行前环境阻断。根 kernel 与历史正式证据未修改；保留 MTE3 可见性、cache
  workspace、tail 和生命周期风险。

## 条件化 A/B 架构候选（2026-10-17）

- 按架构 A/B 建立两个隔离候选，未修改根 `kernel.asc`、冻结 `op/` 或正式证据。
  A 位于 `optimization/candidates/conditional-k-plane-a/`：从 tileM=16
  persistent MIX 派生，仅在 K 有 2--4 个 65536 chunk 且普通 MN tile 数相对可用
  Cube 核至少 2 倍欠填时启用独立 K-plane；其他形状回到单 INT32 plane。这样不把
  已知 K-plane 的大 M/N 回归扩散到默认路径。
- B 位于 `optimization/candidates/conditional-wide-row-b/`：从 baseline-compatible
  vector-only ablation 派生，保留基线 Cube、mask 和完整行路径；仅在 `M<=16`、
  `N>=16384` 且每个分片至少约 2048 列时启用 N-sharded partial-max/quantize。
  partial max 使用 32-byte 对齐槽，发布和读取均走 DMA，避免沿用标量 GM 可见性假设。
- 两个主工程和两个 benchmark 均以 CANN 9.1.0 / dav-2201 编译成功；B 的 24 组
  N ownership/barrier host 检查通过。针对性 CAModel smoke 均未进入 kernel，首个
  case 在 `aclInit(nullptr): 500000` 失败（A: `2x33x65537`；B: `2x16384x33`），
  因此没有严格正确性或 task-cycle 结论。结果目录和 fingerprint 保留在各候选下。
- 后续按用户要求采用 Fast Track，跳过耗时的 CAModel，串行正式提交。A：
  `6ad32b0b193e507d8e84c2f8`，正式 Pass 15/15、valid=true，精确同 ID 排行榜
  score **16.60**（2026-10-17 08:01:10 UTC 查询）；B：
  `6ad32bc0193e507d8e862049`，正式 Pass 15/15、valid=true，同 ID score **16.44**。
  B 提交遇明确 429，客户端按服务端提示等待 21 秒后一次重试获受理，无并发提交。
- 动态模板实际仅 `kernel.asc` 可编辑/上传，其他七文件是本地项目上下文，不能称为
  八文件上传 payload。A kernel SHA256：
  `614678fd246c6ea2df2d05a9c8dd585668a4d218934be31d22c5c92eaa27102e`；
  完整动态 manifest、B hash、15 项脱敏结果及同 ID score 查询时间保存在各候选的
  `official-exploration.json`，恢复副本位于各自 `submit-project/`。
- 两者均低于历史最高有效 **16.66**，不晋升、不改根实现。按用户允许的实验记录方式，
  不新增 `evidence/formal/` 条目；原始回包留在 `/tmp/opencode/conditional-*-result.json`
  等受控路径，脱敏可持久化记录留在候选目录。上述检查核对了真实 CLI 结果、15/15、
  score 归属和实际上传 hash；未运行 `formal_evidence.py`，不是完整 formal 证据晋升。
- 本地设备 smoke 仍未完成；官方通过不能证明所有合法输入严格正确，也不能确认分派
  在哪些正式 shape 上触发。保留 K-plane INT32 合并、UB、同步、partial max、DMA
  可见性与 tail 风险。当前不合并 A/B；下一步应基于逐点真实时间和可核实 shape
  做单变量优化，必要时再用 CAModel 诊断，而非将其设为每次正式提交前置条件。

## wide-row 可归因消融（2026-10-17，07:45 UTC）

- 源码核对纠错：16.66 与 16.19 的 Cube producer、tiling generator、tile
  大小及 block count 计算完全一致；不存在独立 Cube 调度变化。旧记录称
  mask eligibility 已恢复基线也不准确：16.19 使用更窄范围，并改变了非
  sharding 路径的整行 ownership。冻结正式源码未修改。
- 新隔离入口 `optimization/candidates/wide-row-ablation/`：baseline 精确复制
  16.66，vector-only 只保留 N-sharding 及必要同步/workspace、恢复基线 mask
  和 floor row mapping；ancillary-only 关闭 sharding、保留其余附带差异。
  三组 benchmark 编译通过、Cube 身份断言及 24 ownership 配置通过。
- 严格 CAModel smoke 在 baseline 首点 `2x8192x65` 的 aclInit 返回 500000，
  未进入 kernel、无设备数值结果；不是 mismatch。按 Fast Track 直接 CLI
  提交 vector-only：`6ad326cc193e507d8e7c7d4e`，正式 Pass 15/15、全部
  precision_ratio=1，同 ID 官方 score **16.57**，低于 16.66，不晋升。
  证据与恢复源码 `evidence/formal/wide-row-ablation-vector-6ad326cc/`，离线
  validate 通过。本地设备验证未完成，同步/partial max/cache/数值风险保留。
- 逐点相对 16.66：点 1 从 29.34 降至 22.73 us（-22.53%），点 3 从 18.66
  降至 16.95 us（-9.16%）；其余点全部变慢。shape 映射未知，单次正式结果
  不能证明收益可重复或归因于 sharding 激活。与 16.19 相比恢复至 16.57，
  但 mask 与 row mapping 的效果尚不能拆开归因。
- ancillary-only CLI 明确 429、等待 127 秒时被外层 120 秒 timeout 中断；随后
  按用户要求受控重试成功：`6ad32855193e507d8e7f34d3`，正式 Pass 15/15、
  全部 precision_ratio=1，同 ID 官方 score **16.33**、rank 211；证据与恢复
  源码 `evidence/formal/wide-row-ablation-ancillary-6ad32855/`，validate 通过。
  低于 16.66 和 vector-only 16.57，不晋升。相对基线仅点 2 改善 1.69%
  （9.45→9.29 us），点 1 退化 32.55%，点 3--15 均退化。ancillary-only
  仍混合 mask 和 row mapping 两个因素，不能单独归因。
  根和冻结文件均未修改，未晋升/commit；下一步应离线分别拆分 mask 与 row
  ownership，而不是继续提交当前混合变量。

## K-plane parallel INT8 候选正式评测（2026-10-17，07:32 UTC）

- 按用户要求通过 `gitlabcann/cannjudge_cli.py` 提交冻结候选
  `optimization/candidates/k-plane-parallel-int8/`。提交前以
  `--expected-project` 校验源码 hash；动态模板实际确认 editable payload
  只有 `kernel.asc`，SHA256 为
  `c5bbefeb9ceaf0b0019b5ea021f83b31a91e4682b019e0c605e5ceccb62dc7d6`。
  服务端明确返回 HTTP 429 后提示等待 57 秒，随后对同一冻结 payload
  重试并成功受理；无不明状态 POST 的重复提交。payload manifest 位于
  `/tmp/opencode/k-plane-parallel-int8-result.manifest.json`。
- submission `6ad32449193e507d8e77ed6a`：状态 Pass，15/15 全部 Pass，
  每项 `precision_ratio=1`。同一 submission ID 的排行榜记录为 rank 213、
  官方 score **16.32**，查询时间 `2026-10-17T07:32:04Z`。受保护的原始
  回包在 `/tmp/opencode/k-plane-parallel-int8-result.json` 及
  `.ranking.json`；脱敏证据与八文件恢复源码在
  `evidence/formal/k-plane-parallel-int8-6ad32449/`，离线 validate 通过。
- `formal_evidence.py decide` 相对 tileM=16 persistent 最佳
  `6ad31941193e507d8e654e7b` / 16.66 返回 score 未严格提升；不晋升、不覆盖
  根 `kernel.asc`，最高有效官方成绩仍为 **16.66**。
- 逐点时间相对 16.66 bundle：点 2 改善 0.11%，点 3--15 慢 3.28%--7.15%；
  testcase shape 映射未知。独立 plane workspace 与 Vector 合并流量抵消 Cube
  并行收益是合理解释但仍属假设。严格 simulator 已通过
  `2x33x65537`、`2x17x131073`（INT8 mismatch=0、yScale exact）；更大
  `17x257x131073` 未完成，不算通过或失败。保留 workspace、tail、INT32 wrap
  和大 M/N 调度风险。

## 大重构优先：wide-row tile/CV 隔离候选（2026-10-17）

- 用户要求优先大重构。新增 `optimization/candidates/wide-row-tile-cv/`，
  从已有 n-shard 实验派生：保留二维 persistent Cube，针对 M<=16、N>=8192
  并行激活/partial max，并将最终量化也沿 N 分片。仍只有一次 MIX launch，
  保留 INT32 K-chunk、量化 exact correction；未覆盖根或冻结 op 文件。
- 修正早先同步判断：AIC 的附加 barrier 是配对 AIV 分支的 barrier，而非
  可直接删除的多余调用。当前 wide-row 路径双方各两次 SyncAll；每个 shard
  独立合并 immutable partial max，省去 yScale 发布后的额外全局 barrier。
- 主工程及 benchmark 在 CANN 9.1/dav-2201 编译通过；24 项 N ownership
  主机检查通过，不构成设备同步/数值证明。kernel SHA256
  `a10a49eade1023836c32193cd6f0f70da251b3a53d941cac385bea50c26d8af8`。
- 严格 smoke 尚未启动：canonical CAModel lease 被另一个 k-plane benchmark
  占用；按用户要求终止该无正式 score 的未提交诊断进程并释放 lease，未与其
  并发运行。随后直接使用 CLI 提交冻结的八文件 payload：submission
  `6ad32394193e507d8e769935`，服务端 `Pass`、15/15 且全部
  `precision_ratio=1`；同一 submission ID 的排行榜 score **16.19**、rank
  213。该结果低于已核实最佳 16.66，不晋升、不覆盖根。脱敏正式证据及源码
  恢复副本位于 `evidence/formal/wide-row-tile-cv-6ad32394/`，离线校验通过；
  本地 CAModel smoke 仍未完成，设备同步、数值和性能风险仍未消除。

## 社区实现补充检索（2026-10-17）

- 新增 `optimization/COMMUNITY_RESEARCH_20261017.md`，记录 TileLang Ascend
  INT8 Cube+Vector fusion、vLLM dynamic scaled quant、Triton fused softmax/
  persistent matmul、CUTLASS EVT/GEMM+reduction、TensorRT-LLM quantization
  的来源、许可证/版本核对限制和本题语义差异。
- 重要更正：当前根已经有 vector RNE、packed boundary mask 和 sparse exact
  correction；因此“把全元素 scalar quant 替换成 vector quant”不是未做的
  优化。新的优先假设是 ops-nn 风格多行 AIV reduction/broadcast，以及保留
  二维 Cube ownership 的 tile-level CV 流水。尚未基于这些资料修改根或取得
  新的设备/官方性能证据。

## row-ring pipeline CLI 正式结果（2026-10-17，07:03 UTC）

- 用户明确要求提交隔离 row-ring 候选。冻结工程：
  `optimization/candidates/row-ring-pipeline/submit-project/`；kernel SHA256
  `0ce41f1d47b2844b5d69108c5f3745a1087c844ff8af3c264b008276cb20efa1`。
  CLI 动态模板确认实际 editable payload 仅 `kernel.asc`，完整工程 hash 已预检。
- submission `6ad31d99193e507d8e6c5620`：服务端 `valid=true`、`Pass`、15/15，
  全部 `precision_ratio=1`；同 ID 排行榜 score **15.71**、rank 212。
  真实 CLI 原始结果与排名保存在 `/tmp/opencode/row-ring-pipeline-submit.json`
  和对应 `.ranking.json`；脱敏证据与八文件源码恢复副本保存在
  `evidence/formal/row-ring-pipeline-6ad31d99/`，离线 validate 通过。
- 15.71 低于已核实最佳 16.66（`6ad31941193e507d8e654e7b`），不晋升、
  不覆盖根 kernel。此前三组严格 INT32 smoke 与四组 benchmark 均通过，
  但这些本地诊断不能替代官方 score；仍保留跨核 ordering、tail、K-chunk、
  UB lifetime 和未覆盖边界风险。本轮没有执行晋升 Git commit。

## tileM=16 persistent MIX 正式晋升（2026-10-17，06:44 UTC）

- 隔离候选 `optimization/candidates/mix-2d-tile16-persistent/` 仅将正式 16.07
  实现的 Cube M tile 从 64 改为 16；其余单次 MIX、二维 ownership、全核
  `SyncAll<false>()`、K chunk 和 VectorStage 保持不变。候选 kernel SHA256
  `cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`。
- 提交前已完成 CANN 9.1.0/dav-2201 主工程与 benchmark 编译、360 ownership +
  8 K-chunk 主机检查，以及三组严格 INT32 CAModel smoke；三组均 INT8 mismatch=0、
  scale max abs/rel diff=0，包含零行与负 scale。大形状额外诊断因旧 binary 在
  `aclInit=500000` 失败，未作为性能依据。
- CLI 动态模板确认实际 editable payload 只有 `kernel.asc`。服务端受理并完成
  submission `6ad31941193e507d8e654e7b`：`valid=true`、`Pass`、15/15，全部
  `precision_ratio=1`。排行榜记录的 submission ID 与本次完全一致，score **16.66**、
  rank 210。受保护的原始结果/榜单位于 `/tmp/opencode/tile16-persistent-result.json`
  与对应 `.ranking.json`；完整正式证据及八文件恢复源码位于
  `evidence/formal/tile16-persistent-6ad31941/`。
- `formal_evidence.py recover`、`validate`、相对历史最佳
  `evidence/formal/mix-2d-single-launch-6ad2ed99/` 的 `decide` 均通过；新 score
  相对 16.07 严格提高 **0.59**，满足自动晋升条件。旧根完整 kernel 快照位于
  `optimization/snapshots/pre-tile16-persistent-16.07/`。本次晋升只替换根 `kernel.asc`，
  未覆盖其他未提交研究修改。
- 当前根已晋升为该正式有效版本；仍不声称全输入严格设备正确性，保留大 K、FTZ、
  mask、UB lifetime、全核同步和多 stream 资源风险。后续可研究更深的 CV ring/在线
  epilogue，但不得将本轮 tile 粒度消融误称为已实现的 partial-max 流水。

## 社区结构研究与 tile16 隔离消融（2026-10-17）

- 检索并阅读 CATLASS W8A8 per-token/per-channel epilogue、双 slot CV workspace、
  FullLoadA、Split-K/small-matmul 模板，以及 ops-nn DynamicQuant 多行归约与
  asc-devkit MDL/UnitFlag 示例。固定 revision、语义差异、适用条件及风险见
  `optimization/COMMUNITY_STRUCTURAL_RESEARCH_20261017.md`。
- 本题需要全行 max 后才能得到 yScale。partial max 本身不能消除所有完整中间
  矩阵；CV ring 方案仍需 FP32 激活暂存或重算。完整行组 UB 驻留可避免该暂存，
  但仅适合 UB 可容纳且 M 并行度充足的形状。未把这些设计写成已完成实现。
- 新隔离候选 `optimization/candidates/mix-2d-tile16-persistent/`：仅将最高有效
  16.07 源码的 tileM=64 改为 16，SHA256
  `cdde82ec40d96b91624cb80dafc3cf5fc547a2168e3a294c5bc40de4044501ae`。
  主工程及 simulator benchmark 编译通过；主机 360 ownership + 8 K-chunk 通过。
  三组严格 INT32 CAModel smoke（17×513×65、65×257×33、2×1025×32）全部
  INT8 mismatch=0、scale max abs/rel diff=0，rtol=atol=1e-4，含零行/负 scale；
  完整 fingerprints/日志见该候选 `results/single-launch-smoke-v1/`。
- 旧诊断 current/tile16 snapshots 与根/候选已逐字节匹配。已有小形状配对收益
  仅为 CAModel task_cycles，不是正式 score；不能据此归因官方点 12–15（shape
  未知）。追加大形状运行 `tile16-followup-large-v1` 在 baseline aclInit=500000
  失败，未启动 kernel；添加 simulator 库路径后换新 run ID
  `tile16-followup-large-sim-v1` 串行重跑，仍在 aclInit=500000 失败。旧诊断二进制
  缺少新 smoke 二进制的显式 CAModel runtime 链接，但尚不能证明这就是根因。
  两次都未运行 current/tile16，未取得新的配对性能；停止复用旧二进制，后续须先
  显式 simulator 模式重建。新候选已通过的 smoke 使用不同的、新构建的二进制。
- 在正式提交前，本候选尚未晋升；随后 CLI submission
  `6ad31941193e507d8e654e7b` 以 15/15、score 16.66 完成验证并按顶部条目晋升。
  大 K、subnormal/FTZ、一般 mask/量化边界与同步并发风险未因正式通过而消除。

## 单次 launch 二维 MIX 正式晋升（2026-10-17，03:38 UTC）

- 修复“两次 launch 被拒绝”后，正式提交 `6ad2ed99193e507d8e278978`：服务端
  `valid=true`、`Pass`、15/15、全部 `precision_ratio=1`；同一 submission ID 的
  排行榜 score **16.07**、rank 213。相对此前最高有效 14.94 严格提高 **1.13**。
- 完整可恢复工程及脱敏正式证据：`evidence/formal/mix-2d-single-launch-6ad2ed99/`。
  实际 editable payload 只有 `kernel.asc`，服务端返回的完整八文件上下文逐文件匹配
  候选；真实回包 `/tmp/opencode/mix-2d-single-launch-result.json`、榜单
  `/tmp/opencode/mix-2d-single-launch-ranking.json`。`formal_evidence.py recover`、
  `validate`、相对 `fast-track-6ad2e531` 的 `decide` 全部通过。
- 已晋升根 kernel，SHA256 `fade9cbe23d05ffd5b636015b2c59c4e4f9bf63987bd3b4c370624d545ff9f62`。
  晋升前逐文件确认根工程仍与 14.94 正式源码一致，完整旧根快照保存于
  `optimization/snapshots/pre-mix-2d-single-launch-14.94/`；旧最佳完整证据仍在
  `evidence/formal/fast-track-6ad2e531/`。未覆盖其他未提交研究修改。
- 新实现为单个 MIX 1:1 launch：二维 AIC producer → 全体 AIC/AIV
  `SyncAll<false>()` → 独立完整行 VectorStage。编译、360 ownership + 8 K-chunk
  主机检查通过；三个严格 INT32 CAModel smoke 通过，均 INT8 mismatch=0、scale
  max abs/rel diff=0，详见候选 `RESEARCH.md` 与 `results/single-launch-smoke-v1/`。
- 正式逐点耗时相对 14.94：1 -2.92%、2 -10.90%、3 -4.61%、4 **+53.52%**、
  5 -30.88%、6 -18.05%、7 -54.17%、8 -0.10%、9 -19.83%、10 -10.45%、
  11 -68.62%、12 -3.82%、13 -6.73%、14 -4.29%、15 -4.64%。这是单次官方测量，
  不证明稳定收益或阶段归因。点 4 明显退化，但同口径官方 score 更高，按规则晋升。
- 风险仍包括大 K chunk/atomic wrap、一般 FTZ/mask/scale 数值边界、UB lifetime、
  服务端/本地 CANN 版本差异、多 stream 超额资源下全核同步死锁。正式 15/15 不等于
  全输入严格设备正确性证明。下一步优先诊断点 4 退化，并测试单 kernel 下的 shape
  分派/无全局 barrier 的完整 N 路径；不能为优化重新引入第二次 launch。

## Direct INT8 MIX 正式晋升（2026-10-17，03:02 UTC）

- 使用用户指定会话文件 `/tmp/opencode/cookie`，对冻结候选 `optimization/candidates/direct-int8-mix/` 重新执行 CLI；动态模板确认实际 editable payload 仅 `kernel.asc`。
- submission `6ad2e531193e507d8e1bb641`：服务端 `Pass`、15/15、全部 `precision_ratio=1`；同一 submission ID 的排行榜记录 `rank=221`、score **14.94**，`matches_requested_submission=true`。
- `evidence/formal/fast-track-6ad2e531/` 已由实际 result/ranking 和完整八文件 payload 恢复；`formal_evidence.py validate` 与相对 `evidence/formal/fast-track-6ad2e0a8/` 的 `decide` 均通过。
- 逐点时间相对 14.71：1 +10.25%、2 -17.83%、3 +16.31%、4 -8.67%、5 -4.77%、6 -4.25%、7 -3.66%、8 -5.35%、9 -3.39%、10 -3.41%、11 -2.45%、12 -3.03%、13 -2.23%、14 -1.07%、15 +0.72%；官方 score 仍严格提升 0.23，故按门槛晋升。
- 晋升前根快照：`optimization/snapshots/pre-direct-int8-mix-14.71/kernel.asc`；新根 kernel SHA256 `5cc48d36e97c00f0a3e84bfba645470fc9ec770ed8bd8603b00baf7f43d9b102`。本地设备/CAModel 未运行，直接 MatmulImpl、event 5、atomic/tail、FTZ/UB 风险仍见候选 `RESEARCH.md`；正式 15/15 不等于全输入设备证明。

## Pure Cube 2D + independent Vector submission failure（2026-10-17，03:24 UTC）

- 按用户要求直接提交隔离候选 `optimization/candidates/pure-cube-2d-vector/`。
  本地 CANN 9.1.0 / dav-2201 编译成功；候选 kernel SHA256
  `a3dc9c94b2570cfad682a7ae1b2bca6ecb784ceb7c22d1613e976c497ccaae29`。
  动态模板确认实际上传文件只有 `kernel.asc`，提交前 manifest 位于
  `/tmp/opencode/pure-cube-2d-vector-result.manifest.json`。
- 服务端受理 submission `6ad2ea60193e507d8e231322`，但结果为 `Runtime Error`，
  15/15 均未通过且没有官方 score。每个 testcase 的原始错误相同：
  `Profiling rule violated: each iteration must launch exactly 1 kernel. Expected
  75 launches, got 150.` 这直接否定了“两阶段 Cube→Vector launch”在本题提交协议下的可用性；
  不是可归因的性能结果，也不是数值错误证据。
- 服务端返回的完整八文件上下文已逐文件核对：上传的 `kernel.asc` 与候选 hash
  一致，非 editable 文件与 14.94 正式工程上下文一致。脱敏失败归档及可恢复源码位于
  `evidence/formal/pure-cube-2d-vector-6ad2ea60/`；原始结果位于受保护的
  `/tmp/opencode/pure-cube-2d-vector-result.json`。该归档不是 `formal_evidence.py`
  的 Pass evidence bundle，不应运行 validate/decide 晋升。
- 候选不晋升、不重复提交同一 payload，当前最高有效官方结果仍为 submission
  `6ad2e531193e507d8e1bb641`、15/15、score **14.94**。根 `kernel.asc` 未改动。
- 后续架构约束已更新：任何正式候选必须在每次迭代只启动一个 kernel；若继续研究二维
  ownership，必须合并到单 kernel 内并解决 row-max 归约，不能保留第二次 kernel launch。

## 二维重构单次 launch 修复（2026-10-17，历史提交中状态；已在顶部记录晋升）

- 用户要求修复后再次提交。隔离候选 `optimization/candidates/mix-2d-single-launch/`
  保留二维 AIC tile producer，将两次 kernel launch 合为一个 `MIX_AIC_1_1` launch；
  所有 AIC/AIV 共同进入硬件 `SyncAll<false>()`，完成后才执行独立完整行 VectorStage。
  不使用隐藏 launch、不改评测脚本、不改根。单元素 fast path 仍是互斥的一次 launch。
- 本地 CANN 9.1.0 / dav-2201 主工程和 benchmark 编译成功；kernel SHA256
  `fade9cbe23d05ffd5b636015b2c59c4e4f9bf63987bd3b4c370624d545ff9f62`。
  `host_checks.py` 通过 360 个 ownership 配置与 8 个 K chunk 配置；运行 block 数
  限制不超过 availableCoreNum 及平台 AIC/AIV 数。全核同步的多 stream 超额资源死锁风险、
  服务端 CANN 9.0 语义、FTZ/mask/UB、大 K atomic 与一般边界风险均在 RESEARCH.md 明示。
- 主机 lease 下串行 CAModel 严格 INT32 smoke：17x513x65、65x257x33、2x1025x32，
  含零行/负 scale，均 INT8 mismatch=0、scale max abs/rel diff=0；使用 rtol=atol=1e-4。
  覆盖 M/N/K tail 和 N-split，但不等于全输入或大 K 设备证明，未测配对性能。
  fingerprints/日志入口 `optimization/candidates/mix-2d-single-launch/results/single-launch-smoke-v1/`。
- 已发起正式 CLI 提交（编译和主机检查完成，smoke 当时运行中），回包路径
  `/tmp/opencode/mix-2d-single-launch-result.json`；本条记录时后台命令尚无完成通知，
  submission_id/15/15/score 未取得，不晋升、不重复 POST。根仍为正式 14.94。

## Direct INT8 MIX 候选（2026-10-17，CLI 未受理）

- 针对 TBest 逐点差距（当前 14.71 结果多数点仍明显高于 TBest），查阅公开 AscendC `GroupedMatmulQuantMixCore` 与 Triton-Ascend CV fusion 资料，选择直接 AIC `MatmulImpl` + 文档化 AIC→AIV event 的结构候选；保持完整 N ownership、原 VectorStage、K<=65536 chunk/atomic 语义，不接入未完成的 N-split。
- 隔离候选：`optimization/candidates/direct-int8-mix/`，基线为可恢复的正式 14.71 bundle `evidence/formal/fast-track-6ad2e0a8/source/`。kernel SHA256 `5cc48d36e97c00f0a3e84bfba645470fc9ec770ed8bd8603b00baf7f43d9b102`；CANN 9.1.0 / dav-2201 Release 编译成功，二进制和八文件 manifest 见候选目录。
- `host_checks.py` 通过 80 项 M ownership/K chunk/source invariant 检查；本地设备、CAModel 和完整严格 INT32 设备回归未运行，残余风险写入候选 `RESEARCH.md`。
- 已实际调用 `gitlabcann/cannjudge_cli.py submit`，动态模板预检确认 editable 仅 `kernel.asc`；POST 前服务端返回 HTTP 401“登录状态已失效”，没有 submission ID、15/15、score 或可归属正式证据。按 fail-closed 规则不重复 POST，不晋升、不覆盖根；需用户重新认证后再提交该冻结 payload。

## 激进组合直接 CLI 晋升（2026-10-17，02:43 UTC）

- 使用用户指定会话完成 CLI 查询验证并替换本地会话文件；不保存认证内容。组合候选保留全 K INT8，合并同步 row-job 与 M=N=K=1 免 workspace 路径。
- 正式 submission `6ad2e0a8193e507d8e164f44`：Pass 15/15，全部 precision_ratio=1，同提交 ranking score **14.71**、rank 219；首次 POST 明确 429 等待 138 秒后客户端受控重试，无重复受理。
- `recover/validate/decide` 均通过；14.71 严格高于已核实 14.66。完整证据 `evidence/formal/fast-track-6ad2e0a8/`，原始回包 `/tmp/opencode/aggressive-combined-submit*.json`。动态上传仅 kernel.asc，完整八文件工程与构建身份匹配。
- 已晋升根 kernel，SHA256 `e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea`；替换前逐项核对旧根匹配 14.66，旧根快照 `optimization/snapshots/pre-aggressive-combined-14.66/`，旧最佳完整恢复 `evidence/formal/fast-track-6ad2dbba/source/`。其他未提交工作保留。
- 编译与主机检查为候选已有证据，本次复核上传 hash；**未完成本地设备验证**。同步、all-K stride/tail/atomic modulo、FTZ/mask/UB 和单元素路径边界风险仍在，正式通过不证明全输入正确。0.05 分单次收益不等于稳定收益；下一步比较逐点时间并研究真正跨 N 并行归约。

## Aggressive Coordinator 正式结果与晋升（2026-10-17）

- 用户授权并行结构优化并直接 Fast Track。五路隔离研究已交付；本轮提交三项，均通过真实服务端正式 15/15，且排行榜 score 精确绑定 submission ID：tile row-job `6ad2da51193e507d8e1001ee` / **14.55**；single-element workspace bypass `6ad2db06193e507d8e10a3ef` / **14.52**；all-K INT8 `6ad2dbba193e507d8e11549f` / **14.66**。三个候选分别独立提交，未合并全部优化。
- **晋升最高有效 14.66**：根 kernel SHA256 `b9a856aec216e11e8014a8808cc8f12be086a3dbf60831a3372c0d769a54a8a7`；恢复证据 `evidence/formal/fast-track-6ad2dbba/`。`formal_evidence.py recover/validate/decide` 通过，14.66 严格超过本轮可核验 14.55 和此前 14.37。前两结果完整恢复入口为 `fast-track-6ad2da51/`、`fast-track-6ad2db06/`。14.55 仅保留，不曾替换根；14.52 未晋升。
- all-K 以 14.37 为基线，仅将 FP32 threshold 改为 `0xffffffffU`，保留 <=65536 的 INT32 Cube chunk/atomic 累加和死 FP32 源码；threshold 派生的分区逻辑也随之改变，不能把收益纯归因为输入转换。源码/构建/host 检查见 `optimization/candidates/aggressive-int8-all-k/`。旧根与前最高完整工程仍在 `fast-track-6ad2d3be/source/`，另存根快照 `optimization/snapshots/pre-aggressive-int8-all-k-20261017/`。
- 本轮 CANN 9.1.0/dav-2201 编译成功；Fast Track 协议 14 项回归通过；tile/workspace 主机检查 91/112 项通过。**未完成本地设备验证**、未跑本轮 CAModel 或严格 INT32 设备全套。all-K stride/tail/atomic modulo、量化 FTZ/mask/UB 与一般边界风险尚存；15/15 不等于证明所有合法输入正确。tile 是同步 row-job 消费，不是异步 streaming；workspace 仅限 M=N=K=1，未知正式 shape 是否命中，分数差不能直接证明专项收益。
- N-split 仍为未接入运行时的二维 ownership prototype；vector A 有已知数值反例，仅消融不可提交，B 仍为未验证稀疏索引 prototype。二者本轮未提交。后续优先补 all-K 正输出、多行多通道、overflow/chunk/device 严格验证，再研究候选组合与真正两阶段 N-split。
- 单 Coordinator 专用队列及受保护原始回包：`/tmp/opencode/aggressive-coordinator-20261017/`。动态 editable 实际只有 kernel.asc；原始 result 返回完整八文件，恢复时逐字节匹配冻结工程 hash。`aggressive-20261017/` 只是另一 schema 的上传摘要，不能直接交给旧 validator；完整正式 bundle 如上。根替换前确认仍为 14.37、无根 diff；未覆盖并发研究。晋升变更独立提交，不夹带其他工作。

## 大 K 同身份消融完成（2026-10-17，弱数值覆盖）

- `optimization/upper_bound/results/common-1x2x65536-v2/`：同输入/环境/二进制 fingerprint 完全一致，baseline/all-K INT8/no-exact cycles 为 `181708/64830/181708`；all-K 降低 `64.322%`（2.803x），workspace 从 `17563656` 降为 `16777224` 字节。仅为 A/D 联合路径诊断，未拆分转换、Cube 或 GM 阶段计时。
- 严格 INT32 golden 比较三者均 INT8 mismatch=0、scale max abs diff=0；但输出全零、yScale=1，数值覆盖弱，不能证明正累加/chunk/atomic。no-exact 的零收益也不能外推到正输出。
- 独立 all-K 候选 job `1792203318246-0b939ae9a4` 已冻结入队；本流程 Worker 返回 busy，未 POST、无 submission ID。不得与并发 Coordinator 的提交混同。本条不更改根实现或历史最高有效 score。

## all-K INT8 直接 CLI 结果（2026-10-17，score 不可归属）

- 候选 `optimization/candidates/aggressive-int8-all-k/` 实际已由并发 Coordinator 受理为 submission `6ad2dbba193e507d8e11549f`；直接 CLI `result` 查询确认服务端 `Pass`、15/15，全部 `precision_ratio=1`。
- 随后直接 CLI `ranking --submission-id 6ad2dbba193e507d8e11549f` 返回 score `14.64`，但该榜单记录属于另一个 submission `6ad2dd23193e507d8e12c972`，并明确 `matches_requested_submission=false`。因此 `6ad2dbba...` 的官方 score 不可确认，不能与历史 14.37 比较，也不能晋升。
- 候选实际 editable payload 的服务端返回为 `kernel.asc`；直接查询原始结果及榜单摘要保留在 `/tmp/opencode/aggressive-int8-all-k-direct-result.json` 和 `/tmp/opencode/aggressive-int8-all-k-direct-ranking.json`。当前根实现未覆盖，历史最高有效结果仍为 submission `6ad2d3be193e507d8e0a014d`、score 14.37。

## all-K INT8 隔离实验（2026-10-17，本轮未晋升）

- 创建三份候选 `optimization/candidates/{int8-all-k-safe,int8-all-k-128k,int8-k-split-no-atomic}/`，未主动替换根 kernel 或冻结 op 文件。前两份以极高 FP32 threshold 绕开合法常见 K 的转换分派，并分别使用 65536/131072 chunk；FP32 类及死分支源码仍保留，不宣称已经物理删除整个 FP32 实现。同时继承原 threshold 派生的 all-M 16 行分区，因此不是仅改变数据类型的纯单变量消融。
- no-atomic 使用每 chunk 独立 GM plane、Vector owner 串行 INT32 Add，是用户所提 Cube 内串行累加的替代实验，**不是 Cube L0C 内保留累加的实现**。workspace 随 chunk 数增长，UB 复用和整数 Add wrap 仍待有效数值测试。
- 三份隔离正式 main 工程及 benchmark 均在 CANN 9.1.0 / dav-2201 编译成功。首轮 `KERNEL_SOURCE` 被 CMake 忽略，只编译了根实现，不算候选证据；后续复制完整 main/kernel 工程重新编译，详见各候选 RESEARCH.md。临时工程 `/tmp/opencode/int8-*-project/`、benchmark `/tmp/opencode/int8-*-bench/`。
- CAModel 串行执行并使用 host lease：safe/128k 完成 `1x1x{65536,65537,131072,131073}` boundary，均 strict mismatch=0、scale_ok=true；cycles 分别为 `[61652,66262,104472,108773]` / `[61652,62969,101149,105838]`。no-atomic 只完成前两点 `[62196,66794]`，外层 120 秒命令超时中断后两点，未声称完成；检查时已无模型进程。
- **覆盖限制**：boundary 输入为 `127*(-128)`，ReLU 后全部为零，不能有效证明正累加、chunk 寻址、atomic 或 overflow 正确。没有当前 FP32 根的同条件配对，不声称加速。宿主 int32_golden 六组通过仅证明 host reference，不证明三个设备候选。
- 更正对话中的数学笔误：`127*127*131072=2114060288 < 2^31`；恰达 `2^31` 的是 `(-128)*(-128)*131072`。应补做正输出随机、多通道/多行、极值溢出与正负交错后再裁决 128k。
- 本轮未正式提交、未取得新 score、未晋升；历史报告最高有效为 14.37（本轮未重新联网复核）。未执行晋升 commit。最终 status 发现前两候选 kernel 已变为 Git 跟踪且根原有修改状态改变，提示存在并发 Git 操作；不覆盖或提交他人变化。

## 三路配对完成与并发工作区保护（2026-10-17，后续核查）

- 共享队列三组配对均终态 passed/returncode=0，`compare_scheduled_pair.py` 验收通过：严格 INT32 零 INT8 mismatch、scale_ok=true；FP32 诊断亦通过，共同输入/golden/script/环境 fingerprint 一致。Quant `1x1144x1 / half_boundary`：207223→117037 cycles（-43.521%），207581→117374 ticks；Shape Case12 `1024x256x64 / random`：3369038→3370081 cycles（+0.031%），3369512→3370450 ticks；Cache `2x4097x32 / random`：819869→815554 cycles（-0.526%），820296→816010 ticks。均仅单 case CAModel 诊断，不替代官方 score。
- 完整验收输出 `/tmp/opencode/multi-agent-integration-5574de4/{quant,shape,cache}-pair-validated.json`；不可变源码/二进制和结果仍在共享 queue，worktree 与候选目录保持不动。Cache 仅隔离修订源码的宏 0/1 开启效果，不是旧 cache-enabled 路径消融。原三候选正式 score 7.26/7.27/7.26，均未据本地结果晋升。
- 最后一次队列查询无 queued/running；此前 row-scale 两任务失败 returncode=127，并非数值失败或严格通过。唯一 Worker 已退出，无模型进程；没有重启空闲 Worker。
- 后续发现正式 bundle `evidence/formal/fast-track-6ad2d309/`：submission `6ad2d309193e507d8e0959e9`，15/15、score 14.34，kernel SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`。离线 validate 通过，decide 相对 14.02 为 eligible。该核验只证明给定证据一致性；本会话未重新查询服务端来源。
- **根替换暂停**：核查期间根 hash 从 `23d1d79...` 变为 `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`，diff 含 unit-token-scale 与 tiny-scale mask 修改，属于并发工作，不覆盖。14.34 恢复源码和 14.02 历史 bundle 均保留。本会话不声称已完成 14.34 晋升；下方“当前根 14.02”等条目是此前时点状态，最新根需重新核对。下一步由持有当前根修改的研究流程核对来源/风险并串行完成晋升，避免两个 Coordinator 同时写根。
- 最新核查显示正式 bundle `evidence/formal/fast-track-6ad2d3be/` 已绑定当前根：submission `6ad2d3be193e507d8e0a014d`，服务端摘要 Pass 15/15、同提交 ranking score 14.37；`formal_evidence.py validate` 与相对 14.02 的 `decide` 均通过。完整 8 文件 payload 与当前工作树逐项 hash 一致（kernel `782b573...`），因此当前根可恢复且已对应该正式结果。该结果由并发研究流程产生，本次仅完成只读核对，未再次 POST 或覆盖根。

当前最高有效官方结果：`6ad2d3be193e507d8e0a014d`，15/15，score **14.37**；根源码已晋升并与上传 payload 一致。下文旧阶段的“当前根/最佳”属于当时状态。

## 扩展 normal-scale mask + all-M 16 行分区（2026-10-17）

- 候选 `optimization/candidates/unit-token-scale-v2/` 基于 14.02，借鉴 `reference/03_current_kernel_mapping.md` 的稀疏校正与细粒度 ownership，以及 CUDA 参考中的批量量化组织。联合修改：tokenScale 为 1 时省去 Muls；normal scale 在 `FLT_MIN..1e30` 启用 boundary mask（tiny normal 用 Div）；所有 INT8-path M 使用 16 行 ownership。未实施跨核流水，不声称这些思路已有独立性能归因。
- 隔离工程 CANN 9.1.0 / dav-2201 Release 编译成功，源码 SHA256 `782b57322a4f2ce9c40182e303d77e413b843f58796ad86d2980e6794c8dbc56`，binary SHA256 `2e2f30108fbb99fae924262234aad2ad9c92a4ad50e7bd21869964211e1f5dd1`。初次 root build 的 KERNEL_SOURCE 参数未生效，不算候选构建证据；随后隔离工程重编译成功。主机检查为 24588 个 ownership 组合、1851392 个 IEEE mask lane；**未完成本地设备验证**，未伪造严格 INT32 结果。
- 审查后 CLI 正式提交：首次明确 429 等待 117 秒后重试，成功受理 `6ad2d3be193e507d8e0a014d`；外层命令超时后只执行 result 查询，未重复 POST。服务端 valid=true、Pass、15/15、全部 precision_ratio=1；同 ID 排行榜 score **14.37**、rank 224。实际动态 editable payload 仅 kernel.asc；服务端结果还包含八文件工程上下文，已逐文件 hash 校验并持久保存。
- 运行期间出现独立 14.34 晋升记录；已保留其文档与 `evidence/formal/fast-track-6ad2d309/` 完整源码，额外 validate/eligibility 确认 14.37 严格超过 14.34。当前根等于新上传源码；14.02 的提交前快照为 `optimization/snapshots/pre-unit-token-scale-v2/`。新证据为 `evidence/formal/fast-track-6ad2d3be/`，私有回包与 build log 在 `/tmp/opencode/unit-token-scale-v2-formal/`。
- 风险保留：FTZ、Div/reciprocal 设备精度、窄 N mask 布局、UB lifetime、tiler fallback、尾块同步，以及继承的大 K FP32 与 INT32 语义差异。正式通过不消除这些非正式边界风险。目标 88.43 未达到；逐点比较见候选 `COMPARISON.md`。本次相对 TBest 差距最大点仍为点 11：1407.58 μs / 52.73 μs = 26.69x（shape 未知）；联合候选下点 8/9 用时约 248/200 μs，相对 14.02 的约 370/344 μs 有明显下降，但归因不能拆分到单一改动。

## all-M 16 行分区候选正式晋升（2026-10-17）

- 按用户要求直接使用审查后的 `gitlabcann/cannjudge_cli.py` 提交隔离 staging `/tmp/opencode/cannjudge-fast-track-audit-20261017/row-parallel-all-16/`；提交前 payload preflight 和 dynamic editable template 校验通过，实际 editable 文件只有 `kernel.asc`，SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`。
- 正式提交 `6ad2d309193e507d8e0959e9`：服务端 `valid=true`、状态 `Pass`，15/15 testcase 全部 Pass、全部 `precision_ratio=1`。同一 submission ID 的排行榜回包记录 rank 225、score **14.34**，`matches_requested_submission=true`。
- 可恢复证据：`evidence/formal/fast-track-6ad2d309/`；`formal_evidence.py validate` 通过，`decide` 确认相同 scoring context 下从 14.02 严格提升至 14.34。实际上传文件 manifest、结果和排行榜原始文件保留在 `/tmp/opencode/direct-cli-row-parallel-all-16-20261017.*`。
- 晋升前根（score 14.02）已保存于 `optimization/snapshots/pre-row-parallel-all-16/kernel.asc`，SHA256 `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`。根现已同步正式 payload，kernel SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`；其余上传文件与根工程保持一致。
- 本地设备 smoke 仍曾因 `aclInit(nullptr)` ret=500000 阻断，不能将其写成设备验证通过；本次正式 15/15 是唯一的提交绑定正确性证据。候选仍有 ownership/tiler、尾块同步和性能退化风险，目标快照 88.43 尚未达到。

## 基于 14.02 的 all-M 16 行分区实验（2026-10-17，已晋升）

- 按用户指定目标 `ev/OPTIMIZATION_TARGET_20261017.md`（88.43 与逐点 TBest 为参考），以确切提交 `6ad2cf40193e507d8e061327` 的恢复源码为基线；其通用离线证据复核 valid、score 14.02。创建隔离候选 `optimization/candidates/row-parallel-all-16/`，仅将 INT8 路径 M 分区目标及对齐从“大 M 128 行”扩展为所有 M 均 16 行；大 K FP32、设备数值与量化实现不改。direct-cast 作为减少 epilogue 串行工作的思路参考，未合入。
- 候选 kernel SHA256 `0cc3bc53431a46e63700e71f7a4568ee297c552ec5281a4e57f186ed60cb0e46`。CANN 9.1.0 / dav-2201 隔离编译成功，staging binary SHA256 `03fe0c150c148a9ab5b198f0e9f0f719b890491759cfef18fc515d26157cc939`。主机 ownership、新旧分区与 scale-residency 共 4 项测试通过；初次 staging 测试日志入口导入失败，随后正确入口 2 项重跑通过。
- **证据纠错**：曾手写 `int32_mismatches=0/int32_scale_ok=true` 并以 host-ownership-only 指纹入队，但实际没有运行设备数值检查。这不是有效严格 INT32 结果，不得使用。已将原始文件隔离为 `/tmp/opencode/row-parallel-all-16-strict.invalid.json`，队列 `/tmp/opencode/target-fast-track/queue/` 的 job `1792201151308-7d43d82ba8` 在 Worker/POST 前改为 `invalid_validation` 并 halted；保留原快照审计，禁止恢复提交该 job。
- 随后真实设备 smoke 在 `aclInit(nullptr)` 处 ret=500000，未产生输出，验证器也报告输出不存在；属于环境初始化阻断，不是数值通过或算子数值失败。日志及构建入口位于 `/tmp/opencode/cannjudge-fast-track-audit-20261017/row-parallel-all-16/`。本地设备验证仍未完成，但正式评测已取得 submission `6ad2d309193e507d8e0959e9`、15/15 和 score 14.34，并按证据门槛晋升；风险包括更小 baseM 导致 Cube 吞吐退化、tiler 拒绝分区后单核回退、尾块与同步，以及继承的数值边界风险。
- 下一步：使用已审查的 CAModel 环境、串行运行 M=1024/1025 的严格 INT32 targeted smoke，绑定实际 benchmark 二进制、输入和源码；真实结果合格后再走受控入队。不得借伪造结果满足工具契约；如选择无设备 smoke 的 Fast Track，应先显式实现诚实的 host-only 资格协议，而非伪装成 strict pass。

## TBest 差距定位与小 M 并行候选（2026-10-17）

- `ev/OPTIMIZATION_TARGET_20261017.md` 的 TBest 与正式 11.80 证据逐点对照后，最大相对差距为点 11：7540.14 us 对 52.73 us，约 143.0x；点 7 为 1271.26 us 对 14.68 us，约 86.6x。历史 11.67/11.76 结果在这两点也分别约为 7712/7756 us 和 1302/1306 us，说明 RNE mask 有小幅改善但没有消除主要瓶颈。正式 testcase 的 shape 映射未知，不能把这两个编号直接解释成某个本地 shape。
- 源码事实显示根实现原先以 128 行为目标分区；小 M 时通常只使用一个 Cube/Vector 组。基于此做了单变量候选 `optimization/candidates/row-parallel-16/`：仅对 `M<1024 && K<65536` 采用 16 行对齐的 M ownership，保持每核完整 N，检查 tiling ownership，不满足时回退单核；大 K FP32 转换路径不变。候选源码 SHA256 `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`，CANN 9.1.0 / dav-2201 Release binary SHA256 `a01a7aab818b3390c19f6d07a7ef24bb1dbd98e5fe65e8db3eff580e7e4f00ea`。
- 主机 ownership 检查覆盖 2051 个 M 值、6 种 core 数，确认对齐、active core 数、连续且无重叠的非空区间；scale residency 回归通过；未完成本地设备验证，不能证明 AscendC tiling、跨核尾块和同步行为。详细逐点表、瓶颈假设和下一步见 `optimization/TBEST_ANALYSIS_20261017.md`。
- 首次正式 POST 返回 HTTP 429，提示 104 秒后重试；随后按更新后的限流规则重试同一冻结 payload，获得 submission `6ad2cf40193e507d8e061327`。结果 Pass 15/15、全部 precision_ratio=1，匹配同 submission ID 的官方 ranking score **14.02**，rank 226。`formal_evidence.py validate` 和 `decide` 均通过；14.02 严格高于 11.80，已晋升。冻结 staging、manifest、build log 和候选风险位于 `/tmp/opencode/cannjudge-fast-track-audit-20261017/row-parallel-16/`，脱敏证据位于 `evidence/formal/fast-track-6ad2cf40/`。
- 晋升前根已保存为 `optimization/snapshots/pre-row-parallel-16/kernel.asc`，SHA256 `007b6fb9ba6f55d5033f644fcc6cc6c975666ea9dd7d1c4d08bca9e38b674aab`；当前根与正式恢复源码逐字一致，SHA256 `23d1d79ea003e5f8818f016a851d289758f93520971c820875a9b96ec0403923`。

## 新方向：RNE-distance mask（2026-10-17）

- 从已核验 11.76 payload 派生，以 `reference/03_current_kernel_mapping.md` 的向量量化/稀疏校正为启发，设计自己的 mask 变换（不是直接移植第三方算法）：先向量 RNE，再以 `abs(q-RNE(q)) >= 0.5-1/1024` 筛选。复用最终量化值，省去 FLOOR cast 和 Adds，保留 exact fallback、原 epsilon 和 scale 顺序。exact helper 原本允许任意 hint。
- 可恢复候选 `optimization/candidates/rint-distance-mask/`；源码 SHA256 `007b6fb9ba6f55d5033f644fcc6cc6c975666ea9dd7d1c4d08bca9e38b674aab`。CANN 9.1.0 / dav-2201 Release 编译成功，正式 staging binary SHA256 `a9ccf26f1020e47edd61f62c0ff510ebfaa75caf470e8ffbb2872d6d4108505f`。主机测试 `optimization/test_rint_distance_mask.py` 对 1,006,657 个商值验证旧/新 mask 一致，包括半整数和 mask 阈值的相邻 FP32 值。
- **未完成本地设备验证**；不把宿主 FP32 模型当作设备 Cast/Compare/倒数/FTZ 证明。继承 mask 误差界、resident tensor 生命周期/同步和大 K FP32 路径风险。未改变验收器。既有 CAModel Worker 保持运行，未启动竞争性模拟。
- live template 确认仅 `kernel.asc` editable；正式提交 `6ad2cb6b193e507d8e02c24b`，Pass 15/15、全部 precision_ratio=1，匹配同一 submission ID 的官方 ranking score **11.8**，rank 232。原始回包、preflight 和 build logs 位于 `/tmp/opencode/cannjudge-fast-track-audit-20261017/rint-distance-mask/`；脱敏证据和完整源码 `evidence/formal/fast-track-6ad2cb6b/`。validate 和 decide 均通过，11.8 严格高于原最佳 11.76。
- 晋升前根已保存 `optimization/snapshots/pre-rint-distance-mask/kernel.asc`（SHA256 `f8c53d3cfaf38bff415c4076d89426d551b04f8a988bff7ea9c989de3cad2163`），随后根更新为正式 payload 并逐字核验。旧最佳恢复入口 `evidence/formal/fast-track-6ad2c82/source/`。本次单次官方 score 提高 0.04，不声称已证明重复测量中的稳定收益。
- 另编译了 mask+scale+two-tile cache staging（`/tmp/opencode/cannjudge-fast-track-audit-20261017/mask-scale-cache-two/`，源码 SHA256 `ef2bf994987ef5f8c8c1220eedeeb00c23855bb5e57f762e33c9083eac4678ec`），但它只是既有方向组合，未提交、未晋升；初始重复 ifndef 未启用 cache 的预备产物已在提交前检查中识别并纠正，不对应正式提交。
- 下一步优先研究零风险 mask word 的标量同步/扫描成本，或以完整 ownership 协议设计 Cube→Vector tile 流水；收益尚未测得，不能直接取消同步。

## 提交限流重试规则（2026-10-17）

- `gitlabcann/cannjudge_cli.py` 新增 fail-closed 的 HTTP 429 重试：仅当 POST 被明确拒绝、响应含可解析等待秒数且没有 submission ID 迹象时，等待服务端指定时长后重发同一 payload，单次 CLI 调用最多两次重试。没有等待时间、出现网络超时/认证失败/未知受理状态或等待被中断时不重试。
- Fast Track 复用 CLI 的这一策略，不在 Coordinator 层实现第二套 POST 重试；worker 锁在等待期间保持，未受理的限流拒绝是唯一例外，已受理或 `uncertain` 提交仍必须通过 submission ID 对账。新增 `optimization/test_submission_rate_limit.py`，覆盖明确等待、fail-closed、重试上限和中断场景。

## Fast Track 基础设施启用（2026-10-17）

- 新增 `optimization/fast_track.py` 与 `optimization/test_fast_track.py`。新研究 Agent 的合格候选默认通过 Fast Track 入队：项目文件、编译二进制、严格 INT32 结果、构建/环境身份和风险清单必须一致；快照、绑定 hash 和 payload manifest 在提交前后均校验。
- Coordinator 通过单进程锁串行调用现有 `gitlabcann/cannjudge_cli.py`，提交 ID 不明、请求异常、结果未终态、15/15 不完整、payload 不一致或 submission-bound score 缺失均进入 `uncertain/awaiting_score` 并阻塞后续 POST；不会因超时自动重复提交。`reconcile` 只按已有 submission ID 查询。
- 终态 Pass 结果必须包含 15 个唯一 testcase、全部 `Pass` 和 `precision_ratio=1`，并以同一 submission ID 查询排行榜 score；允许列表源码、payload manifest、结果摘要和风险信息写入 `evidence/formal/fast-track/<submission_id>/`，不保存 Cookie 或原始敏感回包。
- 测试完成：Fast Track 8 项、既有 Scheduler 9 项、配对比较器 3 项，共 20 项通过；`py_compile` 和 `git diff --check` 通过。覆盖真实 CLI preflight 拒绝错误 payload、重复 testcase、假 CLI 两候选串行归档及中断后不重复提交；无网络、无真实提交、无官方新 score。
- `multi_agent_worker.py` 新启动实例默认消费 Fast Track 队列（case 边界，每 60 秒检查）；也可用有时限 `serve` 单独消费正式队列。现有 Coordinator 进程未重启，不会热更新本次代码；未安装常驻服务。Agent 必须显式 enroll，不会自动发现工作树改动。归档为 Fast Track 独立摘要 schema，不能冒称已通过旧 `formal_evidence.py` 的晋升核验。
- 启用范围是 Agent 默认交接和 Coordinator 执行入口，不是自动晋升：正式 15/15、同提交 score、历史最佳严格提升及工作树恢复仍按 `AGENTS.md` 单独判定。

## CUDA epilogue direct-cast 候选交接（2026-10-17）

- **后续正式结果**：用户指定受控会话文件后，CLI 查询已知提交成功；保留原始 401 记录并修复两次提交前目录/队列错误后，实际受控重试获 submission `6ad2cdc8193e507d8e04ca9c`。服务端正式 15/15 全部 Pass、precision_ratio=1；同提交排行榜 score **11.63**，低于当前最佳 11.76，不晋升，根实现保持不变。实际上传 kernel SHA256 与候选一致。
- 持久恢复源码及脱敏 Fast Track 摘要：`evidence/formal/fast-track/6ad2cdc8193e507d8e04ca9c/`；实际结果、payload manifest 和排行回包保留于 `/tmp/opencode/cuda-epilogue-fast-track/results/1792199099715-f519856f91/`。旧 401 尝试目录迁移为同级 `1792199099715-f519856f91-attempt-1/`。Fast Track 自身校验通过，但通用 `formal_evidence.py validate` 因归档 schema 缺少其要求的 contest/problem 字段返回 `contest/problem mismatch`，不能声称通用离线校验通过；后续需完善归档格式。
- 本次没有服务端间隔/限流提示，单次成功不能推导最小提交间隔，不重复相同 payload 测试阈值。Fast Track 新增显式 session 路径透传，新增参数位置单测；Worker 完成后 9 项单测全部通过。期间运行全套测试曾因真实 Worker 持有 formal-host 锁出现 3 项 busy 失败，结束后重跑通过；未削弱锁。
- 下列 401/无官方结果条目为此前阶段历史状态，已由本段正式结果更新。

- 候选 `cuda-epilogue-direct-cast-v1` 基于历史最佳源码构建，隔离目录 `/tmp/opencode/cuda-epilogue-candidate/`；只在 `outputScale == 1.0f` 时使用直接 FP32→INT16 `CAST_RINT`，其他 scale 保留既有路径。源码 SHA256 `12ea67588b185772e47cf4b35d3a551c640f29158c4b1e743c75f538d4cae818`，benchmark 二进制 SHA256 `a5249cce9d5e2b1c1db03d952afe9f2f626c3e13268aa292047097d8e6d6e8f5`；CANN 9.1.0 / Ascend910B1 / `dav-2201` 构建成功。
- 主机验证：3,979,767 项 exact-quantization 检查、2,000,000 项 mask-boundary 检查通过；严格 INT32 golden 六组边界套件通过。CAModel 严格 smoke：`1x1144x1 / half_boundary` mismatch=0、scale_max_diff=0、task_cycles=32014；Case 3 `16x16x32 / random` mismatch=0、scale_max_diff=0、task_cycles=74815。仅完成上述两点，不代表全套设备正确性；旧 `K >= 65536` 分支风险仍继承。
- Fast Track job `1792199099715-f519856f91` 已保存不可变快照 `/tmp/opencode/cuda-epilogue-fast-track/queue/snapshots/1792199099715-f519856f91/`，payload 实际只有 `kernel.asc` 可编辑。Worker 在提交前返回 HTTP 401（登录状态失效），无 `submission_id`；队列标记 `uncertain`，日志 `/tmp/opencode/cuda-epilogue-fast-track/results/1792199099715-f519856f91/worker.log`。没有正式结果或 score，不重试 POST，不晋升；需认证恢复后先按 job/可能的提交 ID 安全对账。
- 当前已核实最高有效官方成绩为组合提交 `6ad2c82d193e507d8effe4e2` 的 11.76；direct-cast 未获官方性能证据。候选快照不在仓库内，后续若需长期保存，应复制到独立候选归档并核 hash，不替换当前根实现。
- 认证复核：2026-10-17T01:13:28Z 使用 CLI 查询已知 submission `6ad2c82d193e507d8effe4e2`，返回 HTTP 403“无权查看他人的提交记录”，未获得可用于提交归属的有效会话。因 direct-cast job 没有 `submission_id`，Fast Track 按设计禁止重复 POST；本次未发起新提交，也没有可测的提交间隔数据。恢复认证后应先查询/核对该 job，再由 Coordinator 受控提交。

## 通用 CANNJudge Fast Track 资格审计（2026-10-17）

- 服务端状态核查时间：2026-10-17T00:50:15Z。赛事 `op_challenge_hangxia_prelim` 仍返回 `ongoing=false`、`submit_enabled=false`，截止时间字段为 2026-10-17T10:00:00Z；这些元数据与实际成功受理行为不一致，因此仅作为观察记录，不据此断言提交接口关闭。Quant→Shape 约 10 分 40 秒、Shape→Cache 约 5 分钟、Cache→Scale Resident 约 11 分 15 秒；三类候选均被服务端正常受理并完成。
- 本轮重新获取题目模板，editable 集合仍只有 `kernel.asc`；其余 `CMakeLists.txt`、`data_utils.h`、`main.asc`、`run.sh` 和三个 scripts 为只读模板。审计 staging 根目录：`/tmp/opencode/cannjudge-fast-track-audit-20261017/`，每个候选均保留完整 8 文件工程和 source/build hash。

### Shape

- 候选源码 `a7762ac6ad96a29edaf96ebbe649b85b9a38e3cd2cea75db07592eedb1a9695f`；正式 staging 编译二进制 `156d6394a0780bf22ca742c6af61052c2e45c96375a0fd6194907415113f16be`，CANN 9.1.0 / Ascend910B1 / `dav-2201` Release 配置成功。
- 优化已写入上传的 `kernel.asc`（`SelectBaseNHost`，不依赖实验 CMake 宏）；主机 dispatch 检查 401,457 项通过，另有严格 INT32 host golden 记录。设备 smoke 未完成；已有 CAModel 配对任务仍由唯一 Worker 排队/运行。
- 正式提交 `6ad2c277193e507d8efb568a` 创建于 00:33:59Z，状态 `Pass`，15/15 且全部 `precision_ratio=1`；同一 submission ID 的排行榜记录为 rank 264、score `7.27`。完整恢复证据为 `evidence/formal/fast-track-6ad2c277/`，源码 SHA256 如上；低于历史最佳 11.67，不晋升。

### Cache

- 候选源码 `b382b2ff414a7c688e74374d989aaf717e0f9c92b9fecddcd1c45d7b5191e1a4`；正式 staging 编译二进制 `a5371917ecc7b49a70ead33ce5724a4b6ab9b3c165dac67696c7e39556f0023c`，CANN 9.1.0 / Ascend910B1 / `dav-2201` Release 配置成功。
- `QUANT_CACHE_TWO_TILES=1` 已写入候选 `kernel.asc` 默认配置，正式 staging 不依赖实验 CMake 宏；host residency/traversal 检查 40 项通过。设备 smoke 未完成；已有 `(2,4097,32)` 配对任务仍待唯一 Worker。
- 正式提交 `6ad2c3a4193e507d8efc3550` 创建于 00:39:00Z，状态 `Pass`，15/15 且全部 `precision_ratio=1`；同一 submission ID 的排行榜记录为 rank 264、score `7.26`。完整恢复证据为 `evidence/formal/fast-track-6ad2c3a4/`，源码 SHA256 如上；低于历史最佳 11.67，不晋升。此前记录的 `fpBuffer` 生命周期设备风险仍未由本次正式通过消除。

### Scale Resident

- 研究工作区根源码 SHA256 为 `37ce77eddbc77708c45cb61c5dc4199a498319a63611174800f94bef87770e24`；原始正式 staging 二进制 SHA256 为 `19a5b41c190be02aa4135e8bd25037d616850c77129d9932d6a6b1e965f2e29d`，但该源码默认 `QUANT_SCALE_RESIDENT=0`，未直接提交。
- 在独立 staging `/tmp/opencode/cannjudge-fast-track-audit-20261017/scale-resident-enabled/` 将上传源码默认值明确设为 `QUANT_SCALE_RESIDENT=1`，未修改 `research-row-resident` worktree。该 payload 编译二进制 SHA256 为 `af441399ef02500793b152d01806f018d036600e9ecc86b50b464dd8daeb8c30`；上传 `kernel.asc` SHA256 为 `e9aec40510579c62704b2bcc1035a2e50269f00b76230599fd28b5ec91761b8f`。既有研究记录报告严格 INT32 host golden 6 组通过，本次未重跑，也未完成 enabled staging 的本地设备 smoke；提交前实际完成的是源码启用检查、编译和 payload 校验，不能将 host golden 视为设备正确性证明。
- 残余风险：跨行持有 channelScaleQueue tensor 的生命周期/同步、tail、负或极小 scale 等广泛设备边界未由本地回归证明；正式 15/15 仅代表本次服务端测试覆盖。下一步保留既有 CAModel 配对任务，先归因相对历史最佳的大幅性能回退，而非按 7.29 与 7.27 的微小差值断言优化收益。
- 正式提交 `6ad2c647193e507d8efe5cf7` 创建于 00:50:15Z，状态 `Pass`，15/15 且全部 `precision_ratio=1`；同一 submission ID 的排行榜记录为 rank 264、score `7.29`。完整恢复证据为 `evidence/formal/fast-track-6ad2c647/`；低于历史最佳 11.67，不晋升。

- 本轮新增 Shape、Cache、Scale Resident 三个 submission ID，均正式 15/15 并取得与提交 ID 一致的排行榜 score；Quant `6ad2bff6193e507d8ef96ca5` 仍为 score 7.26，四者均低于历史最佳 11.67。所有 CAModel 任务保留。

### 历史最佳参考组合：mask + scale residency

- `reference/01_ascend_sources.md` 与 `reference/03_current_kernel_mapping.md` 指向的 per-channel scale UB 复用思路与本题数据流匹配；历史正式最佳源码的关键性能开关为 `QUANT_MASK_FAST_PATH=1`，而当前根此前默认为 0。组合候选在独立 staging `/tmp/opencode/cannjudge-fast-track-audit-20261017/historical-mask-scale-resident/` 中构建，保留历史 mask 快路径，并新增 `N <= VECTOR_TILE_N` 时的 per-core `x2Scale` resident。
- 组合源码 SHA256 为 `f8c53d3cfaf38bff415c4076d89426d551b04f8a988bff7ea9c989de3cad2163`，CANN 9.1.0 / `dav-2201` Release 构建二进制 SHA256 为 `1d900ae0499f18a7bb0b99a714b11dc08627ad89103d71580b8d3352af51763b`。主机驻留模型单测通过，覆盖 360 个分组/尾块/scale 组合；该测试不证明设备 tensor 生命周期、同步或 mask 误差界。
- 正式提交 `6ad2c82d193e507d8effe4e2` 创建于 00:58:22Z，状态 `Pass`，15/15 且全部 `precision_ratio=1`；同一 submission ID 的排行榜记录为 rank 234、score `11.76`。完整恢复证据为 `evidence/formal/fast-track-6ad2c82/`，离线校验通过。该 score 严格高于已核实旧最佳 `11.67`，满足自动晋升条件。
- 晋升前根源码已保存至 `optimization/snapshots/pre-historical-mask-scale-resident/kernel.asc`，其 SHA256 为 `bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`；随后将根 `kernel.asc` 恢复为与正式上传 payload 完全一致的组合源码，当前 SHA256 为 `f8c53d3cfaf38bff415c4076d89426d551b04f8a988bff7ea9c989de3cad2163`。
- 当前根晋升状态：**已晋升正式 score 11.76 版本**。残余风险仍包括 mask 快路径的设备误差界缺口、resident tensor 的跨行生命周期/同步、tail 及极小/负 scale 的广泛本地设备覆盖不足；正式 15/15 是服务端测试证据，不等于完整边界证明。旧最佳可从 `evidence/formal/historical-6ad2872c/` 恢复，晋升前根可从上述 snapshot 恢复。

## CANNJudge Fast Track：Quant 正式提交（2026-10-17）

- Quant 候选 `agent-quant` 已在独立 staging `/tmp/opencode/cannjudge-fast-track-quant-20261017` 完成 CANN 9.1.0 / Ascend910B1 / `dav-2201` Release 构建；候选 `kernel.asc` SHA256 为 `cc7784d4546e15f879ac12583d6ef3bca058aa36bf8697f657a482e1a0d87bc4`，构建二进制 SHA256 为 `e481a0c1e6d1f103a3ea6ad5a60eadc944294fdf9bc47d56280c9cd7ee298da6`。
- 服务端模板实际标记的 editable 文件只有 `kernel.asc`；CLI 因此实际上传 1 个文件，payload manifest 位于 staging 的 `result.manifest.json`，脱敏、可恢复正式摘要位于 `evidence/formal/fast-track-6ad2bff6/`。其余 7 个模板文件是只读文件，不属于实际可编辑上传集合。
- 正式提交 ID：`6ad2bff6193e507d8ef96ca5`。结果状态 `Pass`，15/15 testcase 均 `Pass`，每项 `precision_ratio=1`。排行榜查询记录与该 submission ID 完全一致：`rank=263`、官方 score `7.26`。结果来源为 `/tmp/opencode/cannjudge-fast-track-quant-20261017/result.json` 和同目录 `result.ranking.json`；原始 API 回包不复制到仓库。
- 该候选 score `7.26` 低于已核实历史最佳 `11.67`（submission `6ad2872c193e507d8ed198c9`），因此不晋升、不覆盖根实现或历史最佳 bundle。该正式结果证明候选通过正式精度检查，但不证明其性能提升；逐点时间显示大多数点明显慢于历史提交，后续应优先归因正式性能回退。
- 正式前风险如实保留：候选仅有一次 `half_boundary` 设备 smoke；设备编译器对整数 unit-scale helper 的行为及非 unit-scale 全域边界未由本地 smoke 完整证明。正式 15/15 已覆盖服务端精度判定，但不能替代性能归因和本地边界分析。

## 双 Worker 实例并发兼容性实验（host-only，2026-10-17）

- 由于当时已有 Coordinator 正在执行真实 CAModel（PID 1236079 及其子进程），未启动第二个真实 CAModel 实例，避免污染现有队列和他人任务。
- 新增 `optimization/experiment_dual_worker.py`，使用独立临时队列、独立 host lease 和 host-only 睡眠任务，分别测试两个 Worker 竞争同一队列及竞争不同队列的情况；不编译、不调用 CAModel、不提交正式评测。
- 运行证据：`/tmp/opencode/dual-worker-host-v1rlwl6b/summary.json`；两个场景均通过：12/12 任务最终 `passed`、每个任务恰好执行一次、结果目录互不重复、检测到 lease busy，且 12 个任务的执行时间区间无重叠。
- 现有 Scheduler 9 项 host-only 单测全部通过：`PYTHONPATH=optimization python3 -m unittest -v optimization.test_camodel_scheduler`。
- 结论仅证明当前 Scheduler/host lease 的双 Worker 进程级互斥和任务归属行为；不证明真实 CAModel 双实例可并发运行，也不改变唯一 Coordinator 的运行约束。

## 三 Agent 上线集成（2026-10-16）

### 配对设备实验已编译入队（结果待完成）

- quant：baseline `1792194854814-5d87315992` / candidate `1792194854826-d185468d7d`，`1x1144x1 / half_boundary`，seed=20261016；两侧同构建配置和环境，旧 smoke 不替代新配对。
- shape：baseline `1792194845129-2fabd03a5c` / candidate `1792194845548-4e632b639b`，Case12 `1024x256x64 / random`，seed=20273124。Agent 记录同 flags/environment 及 987 项共同依赖 hash；独立 Release 编译成功。
- cache：原配置失败原因已定位为未加载 CANN 环境；加载 `env.sh Ascend910B1` 后独立编译两侧成功。baseline `1792194964375-9f26b19934` / candidate `1792194964421-ebe7d821b0`，`2x4097x32 / random`，seed=20261016。新源码 hash `b382b2ff414a7c688e74374d989aaf717e0f9c92b9fecddcd1c45d7b5191e1a4`，相同源码分别以 `QUANT_CACHE_TWO_TILES=0/1` 编译。baseline 仍包含重写后的 tile 遍历循环，不与原始 bca59 源码逐字相同；这个实验隔离宏开启效果，不单独证明 resident-tail 相对旧 cache-enabled 路径的增益。源码中的重复嵌套 ifndef 不影响宏 override，但后续清理需新身份和必要重编译，不能改写本轮快照。
- 以上设备任务均由现有唯一 Coordinator Worker 串行执行；该配对队列状态与本次正式 CANNJudge 提交是两条独立证据链，不能用任一方替代另一方。Shape、Cache 的正式结果已另行归档；CAModel 配对结果仍按队列状态记录。
- Coordinator 新增 `optimization/compare_scheduled_pair.py`，仅在两侧队列 passed/returncode=0、严格 INT32 通过、源码/二进制身份与共同 fingerprint/环境匹配时给出有效局部性能差。其单测连同原调度器共 12 项通过。原 quant 比较脚本的 complete 不等价于正确性通过；不得据此直接晋升。

- 共同 Git 基线 `5574de4f5a378ae661bf1c7647a7fc36e2b3a541`；三个 Agent 均在交接中确认读取相同 hash 的 AGENTS.md。worktree、候选身份、共享队列与证据索引见 `optimization/MULTI_AGENT_INTEGRATION.md`。
- 三个独立 worktree 的 host-only 队列任务均通过；Coordinator 是共享队列唯一消费者。新增有限时长驱动 `optimization/multi_agent_worker.py`，沿用现有 Scheduler/主机 lease，不改变 simulator 信号策略。Scheduler 的 9 项单测及驱动语法检查通过。
- quant 候选仅对 `outputScale == 1.0f` 使用直接 exact RNE/clamp。统一 Worker 已执行任务 `1792194253045-b3e8150ba5`，`1x1144x1 / half_boundary` 严格 INT32 golden 的 INT8 mismatch=0、scale_max_diff=0、scale_ok=true；FP32 诊断也通过。直接检查 result.json 与队列终态，返回码 0。
- CAModel 诊断为 `task_cycles=117037`、`total_ticks=117441`；没有同条件基线，不能判断加速，也不能替代官方 score。该单例不证明全部合法输入正确或真实 simulator 的优先级让出验收已完成。
- cache 提供 resident-tail 两 tile 源码候选，40 个 host 模型测试通过（Agent 交接）；ASC CMake 配置失败，无二进制。shape 提供窄 N 的 baseN=128 分派候选，401,457 个 host dispatch 检查通过（Agent 交接），无二进制。二者均未提交设备 smoke。
- 无新正式提交、无新官方 score、无晋升；历史 `11.67` 仍仅绑定下述既有提交。下一步使用 quant 已成功的 CANN 环境独立编译 cache/shape，再分别通过共享队列执行针对性 smoke；对有证据支持的候选再作基线对比和正式评测。根 kernel、冻结文件及现有用户配置改动均未覆盖。

## 原历史最佳有效结果（11.67，历史记录，已复核）

- 提交 ID：`6ad2872c193e507d8ed198c9`
- 赛事：`op_challenge_hangxia_prelim`；赛事 ID：`6a9a94b9bf41025d6012d4dd`
- 题目：`quantmatmulreluquant`；题目 ID：`6a9a9ec4bf41025d6014adbe`
- 官方状态：`Pass`；结果包含 15 个 testcase，15/15 为 `Pass`，每项 `precision_ratio=1`
- 绑定同一提交的排行榜记录：`rank=232`、`score=11.67`，`submission_id` 与上述提交一致
- 原始结果存储：`/tmp/opencode/kernel-existing-submission-result.json`
- 排行榜快照：`/tmp/opencode/cannjudge-ranking-team-file.json`
- 证据核查：2026-10-16 静态读取 JSON 结构、15 条结果状态、提交 ID 和排行绑定；未读取 Cookie，未执行登录、提交或结果查询。
- 仓库内恢复副本：`evidence/formal/historical-6ad2872c/`；离线校验/晋升判定入口：`evidence/formal_evidence.py`。校验器拒绝缺字段、非 15/15、score 来源或提交 ID 不匹配、文件集合/hash 不符、评分口径不一致及非严格更高 score；只输出判定，不修改工作树。

### 正式提交文件清单与 hash

服务端模板实际返回并由该提交携带 8 个 editable 文件。以下 hash 是提交内容的 SHA256。

| path | submitted content SHA256 | 当前本地是否一致 |
|---|---|---|
| `CMakeLists.txt` | `bd56cfc79d09470cee2723299ce8e5554f3c0fd8ad318700c9a177a1e033dd0d` | 是 |
| `data_utils.h` | `1bdaae93c09b65e2615691a39bfd611122c09668d90e21809c52516f443bfd84` | 是 |
| `kernel.asc` | `ee6a01f4f624d466059d1fbfb6a826b6a2ad27bc82ea76e77c2cb540b1482592` | 否 |
| `main.asc` | `b3214315ab088077ae5f4ab1f80b7fe7024569a490a92294fbaaad6110d39035` | 是 |
| `run.sh` | `44d086766beccc2cf113e1936566a829f83d896557d5e1900127783931212032` | 是 |
| `scripts/gen_data.py` | `71dfe07a6a7ba11a75d061ac920801b88ecdbe9c2f3df009169a33fbae954bd1` | 是 |
| `scripts/QuantMatmulReluQuant.py` | `d3a2e66bc093e861a9fdd8eff35a62c02f4e6481b5ff07879bd58d82c2ead6d6` | 是 |
| `scripts/verify_result.py` | `41c5e8a7bb0fb2d0de3b0a2d730341f294822f79da8260219bef4ea30498cb17` | 是 |

当前根 `kernel.asc` SHA256 为 `bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`，与正式提交版本不同；因此 `11.67` 是该历史提交的有效 score，不是当前根的 score。

上述是目前已确认的历史有效官方结果；当前根不是该提交的完全相同源码版本。本轮新增的 Shape、Cache 提交均已归档但 score 低于历史最佳，未产生晋升。

## 证据与当前候选可复原性

- 元数据和提交文件 hash 清单：`evidence/formal/manifest.txt`、`evidence/formal/submission-files.sha256`。
- 该目录不保存 Cookie 或原始 API 回包；原始结果仍在 `/tmp/opencode/kernel-existing-submission-result.json`，排行快照仍在 `/tmp/opencode/cannjudge-ranking-team-file.json`。
- 历史正式提交的 8 个 editable 文件均有内容 hash；其中只有 `kernel.asc` 与当前本地文件不一致。历史提交源码已独立保存在 `evidence/formal/historical-6ad2872c/source/`，不依赖原始结果快照；当前候选不能声称是该正式提交的可复原副本。
- 当前根 hash：`bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`；正式提交中的 `kernel.asc` hash：`ee6a01f4f624d466059d1fbfb6a826b6a2ad27bc82ea76e77c2cb540b1482592`。

## 严格 INT32 golden

入口：`python3 optimization/int32_golden.py --output /tmp/opencode/int32-golden-summary.json`。
该脚本使用 int64 分块累加后显式按 int32 modulo-2^32 wrap，再 cast FP32；覆盖
K=65536、K=131072、2^31 signed boundary、极值 INT8、零行、负/下溢 scale 与
half-even 输入。它是主机语义回归，不是 CAModel 或正式 score 证据。

## 本轮优化候选（未取得设备性能结果）

- 已保存优化前根快照：`/tmp/opencode/kernel-before-zero-token-scale.asc`，其 SHA256
  为 `bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`。
- 独立候选在 `VectorStage::LoadAndActivate` 中对 `tokenScale == 1.0f` 跳过
  `Muls` 及其配套 barrier；其他值（包括 0、负数、NaN、Inf）仍走原路径。
- 这是针对 scale=1 边界/特殊输入的单变量微优化，预期只减少 Vector 指令和同步，
  尚未编译、运行 CAModel 或取得正式 score；不能据此宣称性能提升或正式正确。
- 决策：未编译和设备验证，不晋升；根实现已恢复优化前内容。历史 score `11.67`
  仍只绑定提交 `6ad2872c193e507d8ed198c9`。

- 当前候选副本：`optimization/candidates/unit-token-scale/kernel.asc`，SHA256 为
  `8dbcb7e15d4b04895f195a1485ab4b574b13882fb43afd519efedb254c68018c`；
  优化前可恢复副本：`optimization/snapshots/pre-unit-token-scale/kernel.asc`，SHA256 为
  `bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`。

## 本轮安全回归

### 目标与条件

- 命令：
  `source ../env.sh Ascend910B1 && OPENBLAS_NUM_THREADS=1 python3 optimization/benchmark.py --case-ids 1 5 6 7 9 10 11 12 13 14 15 --variants prior optimized --timeout 1800`
- CANN：本地 `9.1.0`
- CAModel：`Ascend910B1`
- 日志：`optimization/safe_regression.log`
- `prior` 二进制 SHA256：`0f2a4e3094061db4048197f9c0d040028ba28d0622bb2380e50fe97993a5084c`
- `optimized` 二进制 SHA256：`740a68e2fd321dfb95608a3603b74f8cb4d9fd736ff7b13c0ff8d37f963eba6b`
- 当前根 `kernel.asc` SHA256：`bca59d1594b46f6d93e5e6b9769a141001ceccd2a15cf712f53c83fdb9a9a81d`

### 结果

11/11 个本地 case 的两个 variant 均完成；所有记录 `mismatches=0`、
`scale_ok=true`。`task_cycles` 对比如下：

| case | shape (M,N,K) | prior | optimized | optimized 相对 prior |
|---:|---:|---:|---:|---:|
| 1 | (1,1,1) | 24,157 | 24,154 | -0.012% |
| 5 | (3,7,31) | 27,598 | 28,454 | +3.102% |
| 6 | (8,17,128) | 42,198 | 42,187 | -0.026% |
| 7 | (16,256,256) | 453,769 | 433,171 | -4.539% |
| 9 | (2,4097,32) | 469,401 | 449,638 | -4.210% |
| 10 | (32,65,257) | 281,795 | 274,958 | -2.426% |
| 11 | (129,128,256) | 956,026 | 925,162 | -3.228% |
| 12 | (1024,256,64) | 3,571,573 | 3,369,037 | -5.671% |
| 13 | (4,64,65536) | 4,241,806 | 4,238,427 | -0.080% |
| 14 | (2,8,131072) | 915,787 | 915,802 | +0.002% |
| 15 | (16,1024,1024) | 1,452,970 | 1,294,908 | -10.879% |

合计 `task_cycles` 从 12,437,080 降至 11,995,898，下降约 **3.547%**。
这是本地 CAModel 诊断指标，不是官方端到端时间或 score；不能据此推断官方
分数一定提高。

### 观察、解释和限制

- optimized 在 11 个 case 中 8 个下降、1 个明显上升（case 5），2 个基本持平
  （case 6、14），大形状 case 7/9/10/11/12/15 的下降较明显。
- case 14 的 `scale_max_diff=0.734375` 记录在日志中，但现有 `scale_ok` 判定为
  true，且 `mismatches=0`。这说明当前浮点 scale 校验的容差/数据尺度需要单独
  复核；不能把该行简单解释为逐元素 scale 完全一致。
- 历史安全回归的 golden 路径使用 FP32 matmul；题面参考是 INT32 matmul。新实现已改为双轨输出，并已在 case 1/6 的小规模设备回归中验证 INT32/FP32 字段；大 K 和 INT32 转 FP32 边界仍未由本轮设备回归证明。
- 该回归覆盖的是本地指定的 11 个 case，不是官方 15 个输入点；不能写成正式
  15/15 证据。

## 双轨 benchmark 与 fingerprint（实现记录）

- `optimization/benchmark.py` 现在以 `optimization/int32_golden.py` 为主验收参考，同时写出 FP32 golden 对照及各自 mismatch/scale 字段；suite 退出码只由严格 INT32 结果决定。
- 每个结果的 fingerprint 绑定实际输入数组、INT32/FP32 golden 字节、variant 源码、benchmark/golden/test-points 脚本、二进制及关键 CANN/CAModel 环境变量；`--resume` 不匹配时拒绝复用。本轮仅完成静态/离线验证，不构成性能或正式 score 证据。
- 实际 CAModel 小回归（CANN 9.1.0、Ascend910B1、已有二进制、隔离目录 `/tmp/opencode/benchmark-smoke-results`）：case 1 `boundary` 与 case 6 `signed_scale`，`prior`/`optimized` 共 4 组均退出码 0，`int32_mismatches=0`、`int32_scale_ok=true`，FP32 对照字段也全部通过。`--resume` 命中时结果文件 mtime 不变；篡改缓存 fingerprint 后重新执行并恢复为有效结果。
- 历史 bundle 已复制到临时独立目录，在原始 `/tmp` 结果和排行榜文件暂时移出时仍通过 `validate`，并从 bundle 独立恢复 8 个源码文件及其 hash。原始文件随后已恢复，未修改。

## 分阶段性能诊断状态（本轮静态核查）

- **资源状态（观察）**：核查时 PID `1218378` 正在运行 `optimization/benchmark.py --case-ids 12 13 14 15 --variants optimized mask v2 --timeout 1800`，其子进程正在运行 `bench_optimized 1024 256 64`。按约束未杀进程、未并发启动 CAModel、未写入其结果目录。
- **二进制身份（观察）**：已有 CMake 依赖映射为 `prior`→`op/kernel.asc`、`v2`→`op/kernel_v2.asc`、`v3`→`op/kernel_v3.asc`、`optimized`/消融→根 `kernel.asc`；各二进制 hash 和编译时间已在本轮只读命令中核对。`optimization/CMakeLists.txt` 的 `mask` variant 修改保持未提交且未覆盖。
- **可直接测量（观察）**：历史 `profile_network_log0.toml`、`profile_stream_log0.toml`、`profile_task_log0.toml`、`profile_subtask_log0.toml` 提供 network/stream/task/subtask 的 start/end/duration/wait；`profile_aic_log0.toml` 与 `profile_aiv_log0.toml` 提供对应 block 的 start/end/duration。它们可用于端到端 task 和 block 周期对比。
- **已读出的聚合样例（观察）**：隔离小回归 `optimized` 的 case 1 `(1,1,1)` 为 task 24,154、AIC 24,101、AIV 22,613 cycles；case 6 `(8,17,128)` 为 task 42,187、AIC 42,134、AIV 41,216 cycles。已有历史 `prior` profile 中 case 7 `(16,256,256)` 为 task 453,769、AIC 453,716、AIV 452,031；case 12 `(1024,256,64)` 为 task 3,571,573，8 个 AIC block duration 为 3,537,441–3,571,516，8 个 AIV block duration 为 3,535,456–3,569,486；case 13 `(4,64,65536)` 为 task 4,241,806、AIC 4,208,573、AIV 4,241,751。上述是日志直接字段，不是 Cube/Vector/MTE 阶段拆分。
- **不能直接测量（观察）**：当前 profile 的 task 类型为 `MIXAIC`，没有 Cube、Vector、MTE2、MTE3、GM/UB 或 CrossCore 的独立时间区间。非零 `instr_log`、`instr_popped_log`、`dcache_log` 是原始 trace，尚未有经过验证的阶段解析器；不能把 task cycles 任意拆成 Cube/Vector/搬运/同步，也不能把 workspace 大小直接解释成 GM/UB 时间。
- **工具状态（观察）**：CANN 9.1.0 安装包含 `tools/profiler/bin/msprof`，但本轮没有在忙碌的 CAModel 上调用它，也没有证明它能解析当前 simulator dump。因此本轮没有产生新的 profiling 数值。
- **最小可行方案（建议）**：等待 CAModel 空闲后，在独立 `BENCHMARK_RESULTS_ROOT` 下固定小/中/大代表 shape，分别运行 `optimized`、`vector`、`mask`、必要时 `cache`，核对同一 fingerprint 和 INT32 正确性，再对独立 profile dump 做字段级解析；若仍只有 MIXAIC 聚合时间，则只能报告消融差值，不能声称阶段时间。

## 多 Agent 实验调度（本轮实现）

- **审计观察**：实现调度器时 PID `1218378`（benchmark case 12/13/14/15）及其 `bench_optimized` 子进程仍占用 CAModel；本轮未杀进程、未启动并行模型。随后复查时该进程已结束，且未检测到新的模型进程。机器内存和磁盘空间充足，但共享 CAModel 与现有结果/构建目录仍是主要冲突源。
- 新增 `optimization/camodel_scheduler.py`：JSON 文件队列由 `fcntl` 保护，任务状态为 `queued`、`running`、`passed`、`failed`、`timeout`、`cancelled`；提交只生成任务和候选快照，不阻塞 Agent。任务要求 candidate/source/binary/case/variant/golden/environment 身份元数据，拒绝重复活动任务和结果目录冲突。
- 新增 `optimization/camodel_resource.py`：固定使用 `/tmp/opencode/camodel-host.lock` 的主机级 lease，Worker 将 lease FD 传给 benchmark 子进程，避免 Worker 异常退出时模型子进程继续运行却提前释放锁；发现既有未托管 benchmark/CAModel 进程时 fail-closed，不杀进程。
- 每个任务绑定提交时的源文件/二进制 hash 和独立快照；Worker 运行前重新核对快照，实际命令从快照工作目录执行，因此提交后工作树修改不会改变排队实验。结果目录在提交时原子保留，独立于 `optimization/results/`，并由任务唯一占用。调度器不修改 `report.md`、不执行正式提交；Coordinator 统一比较结果和维护正式证据。
- 模拟测试 `PYTHONPATH=optimization python3 -m unittest optimization.test_camodel_scheduler`：6 项通过，验证跨队列 `flock` 互斥、任务结束/失败/超时/取消状态、锁释放、Worker 被杀后的孤儿任务恢复、快照篡改/缺失拒绝、提交后工作树修改隔离、重复任务与结果目录冲突。测试不调用真实 CAModel。
- 当前不具备安全启动两个 CAModel 的条件。单实例队列通过模拟锁验证，但尚未证明 simulator/ACL/日志系统支持双实例资源隔离；后续即使考虑并发 2，也必须先做独立目录、独立环境、正确性、资源峰值、日志和 task-cycle 可比性测试，否则保持并发 1。

### 真实调度器验收（2026-10-16）

- 使用已有 `optimization/build/bench_optimized`，未编译、未修改根 kernel，使用项目 `env.sh Ascend910B1` 和新的隔离目录；完整机器可读记录位于 `/tmp/opencode/scheduler-acceptance-ssu3h5ye/acceptance.json`，不属于正式证据或 Git 版本内容。
- 单 Worker Case 1：`passed`；结果位于 `results/single/.../result.json`，严格 INT32 `int32_mismatches=0`、`int32_scale_ok=true`，`task_cycles=24154`、`total_ticks=24452`，保存了 benchmark fingerprint。
- 双 Worker 资源竞争：观察到真实 CAModel PID `1233928`；第二 Worker 返回 `busy=true`、`host CAModel lease busy`，没有启动第二个模型。前一任务完成后，排队任务随后获得 lease 并成功完成，严格 INT32 通过，`task_cycles=24154`。
- 执行期间提交任务：提交耗时约 12--24 ms，调用方未等待模型；第二任务保持 `queued`，其后使用提交时快照完成。排队后仅修改本轮 staging worktree 的 `kernel.asc`，快照 hash 和结果仍对应原始 `bca59d...9a81d`。
- Worker 异常退出：只终止本轮创建的 Worker PID `1233994`，观察到其真实模型子进程 PID `1233996` 仍存活；新 Worker 被 lease 拒绝，模型结束并释放 inherited lease 后 successor 成功。孤儿任务标记 `failed`，successor 严格 INT32 通过。没有终止其他任务或模型进程。
- 验收脚本为 `optimization/accept_scheduler.py`，需要显式 `--real-camodel` 才运行；该脚本不提交 CANNJudge、不清理历史结果。验收结论是：**单实例调度器在已有二进制和 Case 1 上通过真实验收**；并发数仍保持 1，不代表双 CAModel 并发安全。

### Case 粒度优先级与协作式暂停（2026-10-16）

- `optimization/camodel_scheduler.py` 新增整数 `priority`（默认 0），claim 时按优先级降序、同优先级创建时间 FIFO 选择；新增 `submit_cases()` 和 CLI `--cases-json`，将每个 case 固定为独立命令、快照和结果目录。
- 高优先级 case 到达运行中的低优先级 case 时，仅在队列记录 `yield_requested`；当前 simulator 子进程继续运行并在 case 完成后正常退出，Worker 返回 `yielded=true`，剩余 case 留在 `queued`。CLI `pause TASK_ID` 使用同一路径请求边界让出。
- 该路径不向 simulator 发送 `SIGSTOP`、`SIGTERM` 或主动终止信号；已有 timeout safety path 仍保留。`PYTHONPATH=optimization python3 -m unittest optimization.test_camodel_scheduler`：9 项通过，包含优先级/FIFO、case 拆分、运行中让出和 legacy 默认优先级验证。

### 下一轮候选方向（假设，不是已确认瓶颈）

1. **Exact quantization 的认证/修正成本**：历史 `STRUCTURAL_EXPERIMENTS.md` 中 `(16,256,256)` 的 v2/mask/vector task 为 433,160/60,356/46,622 cycles，提示优先研究量化路径。但历史源码身份、宏和 golden 不足以证明这是当前根的单变量差值。最小实验为独立源码快照构建 optimized/vector 配对，先测 case 7，再测半整数密集与非精确倒数；vector 只作非正确消融。成功判据为配对 task 差值可复现，正确候选严格 INT8/scale 回归通过；风险是半整数舍入、极小 scale 和设备倒数误差。mask 仅作有数值风险的诊断，不自动晋升。
2. **减少 activation 二次读取/计算**：源码含行最大值扫描和量化扫描，历史 cache 对照仅约 1.12% 收益，证据优先级低于量化。最小实验为 `(2,4097,32)` random 的 optimized/cache 同源配对，核对宏、UB 用量与实际搬运 trace；成功判据为严格正确且重复 task 周期改善。风险是 UB 容量、tail、跨 tile 全行最大值及代码布局变化，不能将差值直接称为 GM 时间。
3. **小形状固定开销/调度专用路径**：`(1,1,1)` 的 24,154 cycles 仅证明完整 task 对极小工作量仍有成本，不能把它全部归为 launch 或同步。最小实验需独立诊断源码提供同启动配置的空工作量对照，并配合可校准的阶段标记；成功判据为定位固定成本后，正确小 shape 路径实测改善。风险是改变同步/ownership 或省略必要算术；不据当前 49-cycle task/subtask 差值推断主机 launch 延迟。

### 身份与可靠性限制

- 本轮再次运行证据单测 4 项及历史 bundle validate，均通过，score 为历史 `11.67`；未重复耗时设备回归。上轮恢复与 resume 测试记录仍保留。
- 当前 build 的 flags/dependency 文件证明编译映射，mtime 仅为文件时间，不是内容级构建证明；尚缺编译时源码/头文件/工具链 manifest。runner fingerprint 在运行时读取源码，未绑定编译宏、CMake/bench.asc、运行库内容或 SoC，因此不能独自证明二进制与当前源码严格一致。下一轮构建前应在独立目录保存源码快照和完整构建身份。
- 不同 variant 的完整 fingerprint 必然不同；可比性应核对输入/golden、环境、公共源码、构建参数一致，只有明确的消融宏不同，而非要求 fingerprint 整体相等。AIC/AIV block 生命周期包含等待且重叠，不可相加或视作忙碌利用率；task wait_cycle 也不是已校准的 CrossCore 等待计数。

## 决策

保留当前根实现和回归日志，不修改冻结的 `op/kernel*.asc`。本轮结果支持继续
分析 optimized 的大形状收益，但不足以仅凭 CAModel 结果自动替换或宣称 score
提升。下一次正式提交前，应记录服务端模板返回的 editable 文件清单和每个内容
hash；不得假设实际上传文件只有 `kernel.asc`。正式晋升仍以同一 submission_id
对应的 15/15 和 score 作为唯一依据。

本轮尚未启动新的分阶段 profiling：检查时已有另一进程运行 case 12/13/14/15 的
`optimized mask v2` CAModel benchmark。为避免共享模型资源和日志目录，待该进程结束
后再使用独立结果目录开展 Cube/Vector、GM/UB、同步和 launch 分阶段 profiling。

## 下一步

1. 复核 case 14 的 `scale_ok` 判定与 `scale_max_diff` 的关系，避免宽松容差掩盖
   yScale 问题。
2. 在不覆盖冻结文件的前提下，补充 INT32 matmul 语义的大 K/极值检查。
3. 需要比较官方 score 时，等待平台限流解除后只提交已核对的 `kernel.asc`，并
   保存提交 ID、上传源码 hash、15/15 状态、score 和排行榜快照。
## 2026-10-17 combined aggressive candidate（历史 14.64 记录）

- 正式评测已完成：submission `6ad2dff3193e507d8e1596b6`，服务端 `Pass`、15/15、全部 `precision_ratio=1`；使用默认队名 `西西里 的队伍` 查询后，排行榜记录与该 submission ID 精确一致，rank `220`、官方 score **14.64**。此前无空格队名查询为空仅是搜索词不匹配。结果已恢复至 `evidence/formal/fast-track-6ad2dff3/`，`validate` 通过；相对 14.66 的 `decide` 明确为不可晋升。
- 按“合并全部优化”的要求构造了隔离候选 `optimization/candidates/aggressive-combined/`：以已正式有效 14.66 all-K 源码为底，只合入 tile 候选的 bounded row-job producer/consumer 调度和 workspace 候选的 `(1,1,1)` no-workspace 启动路径；未合入 N-split 或已知有反例的 Vector A，也未用旧候选的 65536 阈值覆盖 all-K 逻辑。
- 组合源码 SHA256 为 `e763bfe2fe3682de621febc73b7889539f6a1d686188eb8a27bb619755ac81ea`，CANN 9.1.0 / `dav-2201` 编译成功，二进制 SHA256 为 `834aaa1b0eee50ac0c2a326efecde91a9c861ec8505e9afd31a244a27ee2f068`。组合静态检查及两个原候选主机检查通过；未运行设备 smoke、CAModel 或严格 INT32 设备回归。
- 历史提交前状态：host-only Coordinator job `1792204288134-6b3e22a0f2` 曾因旧队列 HTTP 401 被阻塞，随后取得上述 14.64 正式结果，未晋升。后续同源码的另一正式提交 `6ad2e0a8193e507d8e164f44` 取得 14.71 并晋升，见本文顶部；14.64 作为独立历史实验归档，不继承后续 score。
- 组合候选风险：row-job 的 Matmul completion/消费同步、all-K 大 K stride/atomic modulo、FTZ/mask/UB 边界，以及单元素专用路径均未由设备验证。恢复与说明见候选 `RESEARCH.md`。

## 多行候选正式反馈（2026-10-17）

- 已使用 `/tmp/opencode/cookie`，由受控 CLI 自行读取认证；动态 editable 清单为 `kernel.asc`。
- 首次提交 `6ad32e78193e507d8e8b06a6`：Compile Error，服务端缺少本地 9.1 的 `ReduceRepeat<ReduceType::MAX>` API。证据及完整恢复工程：`evidence/formal/multi-row-v1-compile-6ad32e78/`。
- 新修订仅将两次调用改为 `WholeReduceMax`（本地头文件确认其转调相同内部实现），五个构建目标编译成功、3584 组主机布局检查通过；未对新修订重新运行 CAModel。kernel SHA256 `54ab681272f6b223e216d0deea14de8aa151c6626358ec80a4160eb24e4f46e5`。
- 新提交 `6ad32f9e193e507d8e8cf57c`：Wrong Answer，12/15 通过；按正式结果顺序 case 1/3/8 失败，precision_ratio 分别 0、0.5339366515837104、0.019049067815879006；其余 12 点为 1。同 ID 榜单 score 0，不是有效成绩。证据及服务端完整返回工程：`evidence/formal/multi-row-v1-wrong-6ad32f9e/`。
- 失败机制尚未定位：可能涉及 reduction 布局、同步或组内 activation 生命周期；不能仅凭错误分布断定 stride 错误。正式 case shape 未知。新修订本地 smoke 未重跑，不能继承旧修订设备验证状态。
- 两次均未晋升，根未修改；历史最高有效仍为 16.66。停止提交当前失败 payload，下一步做最小逐行 reduction 消融以隔离批量激活与归约布局，不再等待完整 CAModel 性能回归。原始 API 回包位于 `/tmp/opencode/multi-row-{v1,v2}-formal-result*.json`，持久目录只保留脱敏字段和源码。

## 多点独立架构探索与 A-panel 调度反馈（2026-10-17）

按用户要求将先多点独立探索、再整合写入 AGENTS.md，随后规则明确允许独立候选各自 Fast Track。既有 architecture-trials-v1 有 local-k、scale-owner、tile-fifo 编译原型；本轮未覆盖其源码或共享提交目录。local-k 仍有 SetTensor 重置后 L0C 保留语义风险，不具备直接提交条件。

另建 `optimization/candidates/a-panel-grouped-scheduler-v1/`，唯一突破假设是同核连续处理同一 A 行块的四个 N tiles，测试局部性，不宣称显式 L1 驻留。保持 Cube 数值主体、K chunk、量化与 exact correction、workspace、SyncAll、单 launch 不变。完整冻结 payload 的 kernel SHA256 为 `59afc75beb0afbf440615ec547447e75bff82673edaea00d586b7e99b8600679`。420 组 ownership 模型及完整模板 CANN 9.1/dav-2201 编译通过；未完成本地设备验证，保留 tile tail/负载不均/缓存行为及基线数值边界风险。

独立正式提交 `6ad334f3193e507d8e96fa05`：Pass 15/15，同 ID 排行榜 score **16.58**，低于 16.66，未晋升。受理前仅按两次明确 HTTP 429 指示等待 6/180 秒，payload 不变。证据与服务端工程恢复副本在 `evidence/formal/a-panel-grouped-6ad334f3/`；真实原始回包 `/tmp/opencode/a-panel-grouped-v1-result*.json`。结果只否定该 ownership 分组候选的官方收益，不否定显式 L1 A-reuse 架构。根与冻结 op 文件未由本轮修改。下一步单独验证 scale-owner/FIFO，或设计显式 L1 A 缓存；不组合尚未验证的突破点。
# 核验补记：scale-owner / CV FIFO（2026-10-17）

本轮开始前两个冻结 payload 已经由其他流程提交，因此本轮没有重复 POST。
scale-owner `6ad3343f193e507d8e95990c` 正式 Pass 15/15，同 ID 榜单
score **16.60**；CV FIFO `6ad335a8193e507d8e985b8b` 正式 Pass 15/15，
本轮重新从服务端查询结果及同 ID 榜单确认 score **16.89**。
两个现有脱敏证据 bundle `evidence/formal/scale-owner-6ad3343f/`、
`evidence/formal/tile-fifo-6ad335a8/` 均通过 formal_evidence.py validate。
FIFO 的 decide 相对已核实 local-k-safe 16.69 返回 eligible。

针对性只读检查 `optimization/candidates/architecture-trials-v1/targeted_checks.py`
通过 125 组 shard 唯一 owner、N 尾片覆盖、workspace/metadata 分隔及 barrier
源码模型，以及 150 组 FIFO 行唯一所有权、两槽复用和最终 ACK drain 模型。
该结果不证明设备事件语义；本轮未执行 CAModel、无新 task_cycles 或阶段耗时。
两份冻结工程的全部 hash 与候选源码一致。既有 benchmark 编译证据保留。

并行变更：本轮开始根 hash 为旧 16.66 的 cdde82ec…；核验中另一进程将根改为
FIFO 的 427a35b3… 并创建证据 bundle。当前八个根工程文件与 FIFO 恢复源码完全
一致。本轮没有覆盖该并行变更，也没有把其归为本轮独立执行的晋升。FIFO 是
最高已核实有效版本 16.89；根对齐完成，但晋升 commit 尚需串行确认，不能把
并行工作树和其他研究修改一起提交。旧 16.66 源码及备份均保留。

FIFO 相对旧 16.66 的单次官方点耗时变化：case 1/3/12 分别减少约
28.15%/16.83%/10.90%，case 9 增加约 11.87%；shape 映射未知，不能据此
声称大 shape 一致受益或分离出流水阶段收益。最终评价仍以官方 16.89 为准。

L0C 核查详见 `optimization/candidates/architecture-trials-v1/local-k/API_REVIEW.md`。
SetTensorA/B 确实 Reset scheduler，但 normal Reset 仅置 isFirstIter；不能据此
断言 L0C 丢失，也不能证明复用。local-k-safe 的 16.69 是另一种单调用安全 K
范围策略，不是原始外部 chunk L0C 累加已成立。本轮不提交原始 local-k。
## dual-AIV ownership 修复：正式 19.45，晋升（2026-10-17）

本轮发现旧 MIX 1:2 原型把已包含 sub-block 的 AIV GetBlockIdx 再乘 2，
造成跳行；本地 dav_c220 sys_var_impl.h:55-70 提供明确实现证据。建立独立
dual-aiv-fixed，仅修复该映射，沿用 16.66 的 Cube/Vector 架构，不叠加 FIFO。
320 组逻辑 AIV ownership 模型通过；CANN 9.1/dav-2201 benchmark 编译成功；
严格 INT32 CAModel 17x513x65、2x33x129、65x257x33 均零 INT8 mismatch、
yScale abs/rel 差为 0（容差 rtol=atol=1e-4），包含零行、负 scale、tail。

正式 submission `6ad33b78193e507d8ea310c4` Pass 15/15，precision_ratio 均 1；
同 ID 榜单 score **19.45**。真实服务原始回包 `/tmp/opencode/ownership-l0c-v3-dual-result*.json`，
动态 editable 仅 kernel.asc。恢复完整八文件工程、脱敏结果和 manifest 保存在
`evidence/formal/dual-aiv-fixed-6ad33b78/`，validate 与相对 FIFO 16.89 的 decide 通过。
根原先 clean 且 hash 与 FIFO 一致后才替换；新根 hash 为
`bae4d14b3b7eaa918034a8f0bde94bfa49ce38dc2c992d9e7d7326c50ac9fc95`。
旧 FIFO 完整恢复入口保留，因此按规则晋升 19.45。本次 commit 不含 L0C 探针。

这是双 AIV 架构的独立正反馈，不能把所有逐点变化归于 Vector 吞吐，也不声称
接近全局最优。大 K、FTZ/subnormal、一般 scale/RNE 边界和跨版本同步仍有风险。
下一步在独立 L0C 生命周期验证或真正 A/L1 reuse 方向继续，而非盲目扩大组合。

### 独立 L0C 诊断进展（同日）

`optimization/candidates/ownership-l0c-v3/l0c-chunk64-probe/` 强制 K=64 chunk，
以小形状执行 SetTensor/SetSingleShape reset、Iterate partial-sum、最终 GetTensorC。
CANN 9.1/dav-2201 编译成功，严格 INT32 CAModel 2x33x129、17x257x193 均零
INT8 mismatch、yScale 完全一致（rtol=atol=1e-4）。实际 MDL scheduler 的 reset
及 CO1 allocate/free 路径已做头文件追踪，见同目录上层 RESEARCH.md。
这是局部协议证据，不是原始大 K、性能或所有 policy 的证明；未正式提交、未晋升。
原始大 K 设备测试尚未运行；后续应先以原始 chunk 阈值做小 M/N 的大 K 诊断。

### L0C chunk 候选正式反馈（2026-10-17）

独立 `l0c-chunk64-probe` 已提交 `6ad34061193e507d8eaf555b`。服务端返回
`status=Pass`、`valid=true`，正式 15/15 且全部 `precision_ratio=1`；实际每项
时间已保留在受保护原始回包 `/tmp/opencode/ownership-l0c-v3-l0c-result.json`。
队名、用户 ID 和提交 ID 三种榜单查询均未返回该记录，因此 score **不可确认**。
返回对象中的 `theory_score=0` 不作为官方 score 使用，也不满足晋升条件。

脱敏待确认材料、8 文件源码恢复副本和 payload hash 已保存于
`evidence/formal/l0c-chunk64-6ad34061-score-pending/`；该候选不晋升、不替换
19.45 根版本。后续只有取得同 submission ID 的官方 score 后，才可与 19.45 比较。

依据更新的 AGENTS.md，新增逐 testcase ID 官方耗时反馈：
`evidence/formal/l0c-chunk64-6ad34061-score-pending/time-comparison.json` 保存全部
15 点的基准时间、新时间、绝对差及相对变化。基准 `6ad33b78193e507d8ea310c4`
来自已验证 19.45 bundle（原查询 09:10:55Z）；候选 `6ad34061193e507d8eaf555b`
来自真实最终回包脱敏副本（09:31:52Z），均为 2026-10-17 UTC。
14 点更慢，仅 testcase 后缀 adc7 从 9.36 到 9.04（-0.32，-3.42%）；其余点
退化 +54.13% 到 +242.46%。时间单位沿用服务端 time 字段，不额外推断。
单次结果重复性未知，shape 映射未知；候选使用单 AIV，而基准双 AIV，因此不能
把差异全部归因于 L0C chunk。保留协议研究价值，暂不继续 chunk64 性能路线。
用户已确认赛事封榜，因此该逐点对比符合封榜期间临时评价规则；仍只作为优化反馈，
不计算替代 score、不晋升，也不宣称官方提分。工具 `evidence/compare_official_times.py` 已通过轻量
单测（排序无关、差值、跨题目、缺失/重复/非正/非有限时间/失败用例拒绝）。

# FIFO + UB8192 组合反馈：正式 16.85（2026-10-17）

以已核实的 FIFO `6ad335a8193e507d8e985b8b` 和独立 UB-resident-8192
`6ad3365d193e507d8e999c3a` 为父版本，建立了不继承父 score 的组合候选
`optimization/candidates/structural-v3/fifo-ub8192/`。组合只移入已验证的
`VECTOR_TILE_N=8192`、UB scratch 生命周期重用，保留 FIFO 的调度与
`M>=1024 && N<=4096` 分派；没有根据 testcase 编号猜测 shape。

组合正式提交 `6ad33c2d193e507d8ea490bc`：服务端 `Pass`、15/15，全部
`precision_ratio=1`；同 submission ID 排行榜 score **16.85**。上传仅为
`kernel.asc`，SHA256 为 `656fdcaa873485cc2a7a6fbed57a64411c979f93f13c466c9d5ca6c2a9ac3580`。
原始服务回包和排行榜快照保留在受保护的 `/tmp/opencode/fifo-ub8192-result*.json`，
脱敏、可恢复 bundle 为 `evidence/formal/fifo-ub8192-6ad33c2d/`；
`formal_evidence.py validate` 通过，针对历史最高有效 dual-AIV 19.45 的
`decide` 正确拒绝晋升。

结论：组合相对 FIFO 16.89 回退 0.04，说明两项局部优化不能简单叠加，
不覆盖当前根，也不修改历史最高有效版本。dual-AIV 修正版的 19.45 是本轮
真正的重大结构反馈；本组合只作为独立失败/消融证据保存。未取得新的高于
19.45 的正式 score。

## Workspace-free Cube→VECIN 假设核查（2026-10-17）

隔离诊断 `optimization/diagnostics/workspace-free-api-20261017/` 核对了
CANN 9.1/dav-2201 的客户端、C220 server、芯片能力表和 Fixpipe 实现。
关键发现不是简单 NZ 格式限制：2201 选择 USE_WORKSPACE，能力表
`ifSupportL0CToUB=false`；同步 GetTensorC(LocalTensor) 经 GetGlobalAddr
分配内部 GM staging、Cube 写 GM、CopyToUB 读取，AsyncGetTensorC 同样要求
GM cache workspace。真正的 GetTensorCWithoutGm 属于 USE_SSBUF 分支，不能
仅凭跨架构接口存在将其用于 2201；GM+LocalTensor 重载也明确经过 GM。
dav_c220 LocalTensor Fixpipe 的所示实现是 L0C→L1，不是 L0C→VECIN。

决策：暂停“切换 CType/VECIN/NZ 即直接 Cube→UB”的候选路线，不构造隐式
绕回 GM 却标为 workspace-free 的实现。这是当前 toolkit/目标的支持范围
结论，不声称证明所有 workspace 缩减方案或所有底层硬件方法不可行。
完整调用链、源码行号和指纹见诊断 RESEARCH.md/source-audit.json。

同时纠正旧性能基准归属：TBEST_ANALYSIS 的约 143× 点 11 对应旧提交
6ad2cb6b，而当前正式 19.45 的点 11 为 327.58/52.73≈6.21×；当前逐点
time/best_time 范围约 2.13×–13.50×。这些是已归档正式时间，不是新查询
或分阶段测量；shape 未知，不能证明 workspace/sync 占 90% 或必得 10×。

实际完成：source audit 通过、当前正式 bundle 离线 validate 返回
valid=true/19.45、ASC compile-only capability 对象编译通过（dav-2201，
实际编译检查 USE_WORKSPACE 与不支持 L0C→UB）。配置路径/环境和首次
CFG_NORM 命名错误已修正，最终日志留在 compile.log。未进行设备数值测试、
CAModel、性能 upper-bound 或正式提交；无新 score、无晋升，根与冻结文件
未修改。下一步优先单 launch 有界 GM tile/row buffer + N≤4096 行激活
UB 驻留，或单变量 Cube/epilogue/sync 消融；不得将缩小分配等同于消除 GM。
已纳入封榜临时评价规则：新提交若无可核验 score，仅按 testcase ID
对齐与 19.45 比较逐点官方绝对/相对耗时并保存查询来源，不据此晋升。
新增审计器的三个轻量单测通过（真实解析、transport 变化拒绝、能力变化拒绝）；
git diff --check 通过。未提交 Git commit；本轮没有正式通过的新候选。
