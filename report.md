# QuantMatmulReluQuant 研究与决策记录

更新时间：2026-10-17

当前最高有效官方结果：`6ad2c82d193e507d8effe4e2`，15/15，score **11.76**；根源码已晋升并与上传 payload 一致。下文旧阶段的“当前根/最佳 11.67/未晋升”属于当时状态，组合晋升事实见“历史最佳参考组合：mask + scale residency”。

## Fast Track 基础设施启用（2026-10-17）

- 新增 `optimization/fast_track.py` 与 `optimization/test_fast_track.py`。新研究 Agent 的合格候选默认通过 Fast Track 入队：项目文件、编译二进制、严格 INT32 结果、构建/环境身份和风险清单必须一致；快照、绑定 hash 和 payload manifest 在提交前后均校验。
- Coordinator 通过单进程锁串行调用现有 `gitlabcann/cannjudge_cli.py`，提交 ID 不明、请求异常、结果未终态、15/15 不完整、payload 不一致或 submission-bound score 缺失均进入 `uncertain/awaiting_score` 并阻塞后续 POST；不会因超时自动重复提交。`reconcile` 只按已有 submission ID 查询。
- 终态 Pass 结果必须包含 15 个唯一 testcase、全部 `Pass` 和 `precision_ratio=1`，并以同一 submission ID 查询排行榜 score；允许列表源码、payload manifest、结果摘要和风险信息写入 `evidence/formal/fast-track/<submission_id>/`，不保存 Cookie 或原始敏感回包。
- 测试完成：Fast Track 8 项、既有 Scheduler 9 项、配对比较器 3 项，共 20 项通过；`py_compile` 和 `git diff --check` 通过。覆盖真实 CLI preflight 拒绝错误 payload、重复 testcase、假 CLI 两候选串行归档及中断后不重复提交；无网络、无真实提交、无官方新 score。
- `multi_agent_worker.py` 新启动实例默认消费 Fast Track 队列（case 边界，每 60 秒检查）；也可用有时限 `serve` 单独消费正式队列。现有 Coordinator 进程未重启，不会热更新本次代码；未安装常驻服务。Agent 必须显式 enroll，不会自动发现工作树改动。归档为 Fast Track 独立摘要 schema，不能冒称已通过旧 `formal_evidence.py` 的晋升核验。
- 启用范围是 Agent 默认交接和 Coordinator 执行入口，不是自动晋升：正式 15/15、同提交 score、历史最佳严格提升及工作树恢复仍按 `AGENTS.md` 单独判定。

## CUDA epilogue direct-cast 候选交接（2026-10-17）

- 候选 `cuda-epilogue-direct-cast-v1` 基于历史最佳源码构建，隔离目录 `/tmp/opencode/cuda-epilogue-candidate/`；只在 `outputScale == 1.0f` 时使用直接 FP32→INT16 `CAST_RINT`，其他 scale 保留既有路径。源码 SHA256 `12ea67588b185772e47cf4b35d3a551c640f29158c4b1e743c75f538d4cae818`，benchmark 二进制 SHA256 `a5249cce9d5e2b1c1db03d952afe9f2f626c3e13268aa292047097d8e6d6e8f5`；CANN 9.1.0 / Ascend910B1 / `dav-2201` 构建成功。
- 主机验证：3,979,767 项 exact-quantization 检查、2,000,000 项 mask-boundary 检查通过；严格 INT32 golden 六组边界套件通过。CAModel 严格 smoke：`1x1144x1 / half_boundary` mismatch=0、scale_max_diff=0、task_cycles=32014；Case 3 `16x16x32 / random` mismatch=0、scale_max_diff=0、task_cycles=74815。仅完成上述两点，不代表全套设备正确性；旧 `K >= 65536` 分支风险仍继承。
- Fast Track job `1792199099715-f519856f91` 已保存不可变快照 `/tmp/opencode/cuda-epilogue-fast-track/queue/snapshots/1792199099715-f519856f91/`，payload 实际只有 `kernel.asc` 可编辑。Worker 在提交前返回 HTTP 401（登录状态失效），无 `submission_id`；队列标记 `uncertain`，日志 `/tmp/opencode/cuda-epilogue-fast-track/results/1792199099715-f519856f91/worker.log`。没有正式结果或 score，不重试 POST，不晋升；需认证恢复后先按 job/可能的提交 ID 安全对账。
- 当前已核实最高有效官方成绩为组合提交 `6ad2c82d193e507d8effe4e2` 的 11.76；direct-cast 未获官方性能证据。候选快照不在仓库内，后续若需长期保存，应复制到独立候选归档并核 hash，不替换当前根实现。

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
