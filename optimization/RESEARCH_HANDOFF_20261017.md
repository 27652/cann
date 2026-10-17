# 紧急停止后的研究收尾与未完成成果（2026-10-17）

## 范围与证据等级

本交接整理四个会话末期涉及的研究成果：A/L1 正式反馈归档、A/L1 提交与
后续获分、N-tile/TBest 逐项对照，以及 Cube→VECIN / workspace-free
接口核查。以下按可恢复的 Git、源码和结果记录状态，不建立未经核验的
session ID 映射。A/L1 反馈归档与提交关联同一候选与同一 submission，
不能算作两个独立算法、两次正式提交或两份独立性能证据。
`MULTI_AGENT_INTEGRATION.md` 的 quant/cache/shape 是更早的三 Agent 实验，
不能据名称相同认作这里的末期会话。

本次只做 Git 归档、源码/证据一致性及轻量测试，不启动 CAModel、编译、
Worker、正式提交或后台续跑。历史设备结果只在其原 fingerprint 范围内有效。
最终有效基准仍为 `6ad345e2193e507d8ebb20ec`，15/15、score **19.48**、
查询时 rank **195**；晋升 commit `b60f59c3a516a590ba967070b9dc6a94b1be0070`。

## A/L1 正式反馈归档：commit ba58a6b

- 完整 commit：`ba58a6b3b7e6e0b1ebc40e3b039ac49ed275e532`，
  时间 2026-10-17 09:58:11 UTC，标题 `Record dual-AIV A-L1 formal feedback without promotion`。
- 已保存 23 个文件：A/L1 研究记录、完整八文件源码、上传 manifest、
  四组 strict 结果及 fingerprint、pending-result、空 ranking、逐点耗时比较。
- 当时最后状态：`6ad345e2193e507d8ebb20ec` Pass 15/15，但尚无同 ID score，
  不晋升。未完成的是 score 归属确认，以及更广回归/性能归因；不是没有提交。
- 后续 score 已由 CLI 核实为 19.48，晋升由 `b60f59c` 独立保存。
  该 commit 的 pending 状态属于历史观察，不能据此否定后来的有效成绩。

## A/L1 提交与后续获分：dual-AIV + A/L1 复用

- 入口：`candidates/dual-aiv-l1-v4/RESEARCH.md`、`prepare.py`、
  `revise_stride.py`、`checks.py`；父版本、初版、stride16 修订分别可恢复。
- 停止前曾编译完成但 smoke 被全机 lease 拒绝；后来恢复串行运行四个严格
  INT32 smoke：17x1025x64、65x513x256、17x257x4096、fallback 17x513x65。
  已记录零 INT8 mismatch、yScale exact；175 组 host ownership/NZ 模型通过。
- 初版 `a-l1-group4` 保留 full-M SetOrgShape 与 16-row NZ 面板跨度不一致的
  已知风险，不能作为合格候选；stride16 修正为 tileM。
- 后续正式 `6ad345e2193e507d8ebb20ec` 获分 19.48 并晋升。这是**停止后完成**，
  不应把早期“未完成设备验证/score pending”重写成当时已经通过。
- 未完成：同条件父/子性能配对、group size 单变量消融、调度粒度与 L1 流量
  效果分离、更广 tail/core count/L1 coexistence/large-K/FTZ 边界验证。
- 恢复：使用冻结父/子工程；先检查 `checks.py --help` 和源码参数，再运行
  host 检查。设备实验需重新获取 lease、建立新 fingerprint，不能重用旧二进制。

## N-tile early-max 与 TBest 逐项对照

- 最后产物 `candidates/n-tile-max-pipeline/TBEST.md` 按 testcase ID 对齐
  FIFO、dual-AIV 19.45 与该正式回包的 TBest，包含全部 15 点及差值/比例。
  这是历史 19.45 基准对照，不是最终 19.48 的重测，更不是新候选正式结果。
- 表中 dual/TBest 为 2.13x–13.50x，绝对差较大的是点12–15；shape 未知，
  不以此推断分阶段瓶颈或可实现的组合上限。`tbest.py` 与输入证据一起保留。

- 入口：`candidates/n-tile-max-pipeline/{RESEARCH.md,kernel.asc,prepare.py,smoke.py}`。
  父版本为 FIFO 16.89，不是最终 dual-AIV 19.48。
- 默认仅 M>=1024、4096<N<=16384 启用；两条 outstanding tile 通道，
  ready 4/5、consumed 6/7、row-complete 8、row-consumed 9。
  保留完整行 GM slot，AIV 提前更新 max，量化仍重读行；不是全局动态队列。
- 默认及 probe 编译通过；strict INT32 probe：17x4097x33、17x8201x33、
  65x4097x33，单核三 row-job reuse 33x4097x33 通过；fallback
  33x16385x33 通过。全部记录零 mismatch、yScale exact。
- **未完成/阻断**：默认生产分派 1025x4097x33 在 240 秒超时；不能判为通过，
  也不能仅据超时判死锁。没有正式提交，没有同条件性能配对或 score。
- 风险：跨核可见性、event drain/slot reuse、每 tile 事件开销；当前一 AIV
  可能损失双 AIV 吞吐。跳过 FindRowMax 时必须关闭 QUANT_CACHE_TWO_TILES。
- 下一步：先区分生产形状的进展/死锁/模拟器耗时，再做严格回归和配对；
  未独立验证前不要直接与 A/L1 或 dual-AIV 组合归因。

## Cube→VECIN / workspace-free API 可行性核查

- 入口：`diagnostics/workspace-free-api-20261017/{RESEARCH.md,audit.py,
  test_audit.py,capability.asc,CMakeLists.txt,source-audit.json,compile.log}`。
- 已完成 CANN 9.1/dav-2201 源码调用链审计、三个轻量单测、compile-only probe。
  能力表 `ifSupportL0CToUB=false`，当前 LocalTensor GetTensorC 实际经内部
  GM staging；USE_SSBUF/GetTensorCWithoutGm 不可直接移植为本目标能力。
- **没有算子候选、设备数值验证、CAModel 性能数据或正式提交**。
  capability.asc 不是完整算子，不能上传。结论是当前接口路线不支持，
  不是证明所有 workspace 缩减方法或硬件路径均不可能。
- 未完成：有界 GM row/tile buffer、N<=4096 activation UB 驻留的新实现，
  Cube/epilogue/sync 单变量消融及真实计时归因。
- 审计记录绑定历史 19.45 根；最终根已晋升。旧 source-audit.json 保留历史
  hash，不篡改为新根检查结果；重跑需显式选择历史基准，见 audit.py --help。

## 其他保留成果及失败原型

| 入口 | 实际状态 / 未完成项 |
|---|---|
| `candidates/multi-row-epilogue-v1/` | ReduceRepeat 版本本地定向测试通过，正式 Compile Error；WholeReduceMax 修订正式 Wrong Answer、12/15，原因未定位，不能继承旧修订 smoke；需最小逐行 reduction/activation 生命周期消融 |
| `candidates/n-shard-single-launch/` | 初版 2x8192x65 严格失败（3686 mismatch）；改为 aligned DMA partial-max 后未完成设备复测；无正式提交 |
| `candidates/architecture-trials-v1/local-k/` | 外部 chunk 的 L0C 生命周期/SetTensor reset 语义不明，保留 API_REVIEW 与源码，不等同于已获分 local-k-safe |
| `candidates/structural-breakthrough-v2/dual-aiv/` | 初版 ownership 严格失败；保留失败源码，与 ownership-l0c-v3 修正版区分 |
| `candidates/structural-v3/` | FIFO+UB8192 正式 16.85，低于父 FIFO 16.89；组合未晋升；dual-aiv-corrected 探针不继承其他修订分数 |
| `candidates/wide-row-ablation/` | vector-only 16.57、ancillary-only 16.33；无提分，混合因素未完全分离 |
| `candidates/pure-cube-2d-vector/` | 正式 Runtime Error，失败证据位于 `../evidence/formal/pure-cube-2d-vector-6ad2ea60/`（相对 optimization） |
| `candidates/row-ring-pipeline/` 及其他 results | 保留源码、结果与 fingerprint；历史局部结果不提升为最终有效 score |
| `../evidence/formal/tile16-persistent-pending/` | 旧工程/上传 manifest 快照，不代表又有一次新提交或未知新成绩；正式已获分恢复入口以 roadmap 为准 |

## 归档与恢复约定

- `research-archive-20261017/manifest.json` 逐项记录本次新增研究文件路径、
  字节数及 SHA256；`excluded.json` 记录未纳入 Git 的生成物路径/原因。
- 保存研究源码、CMakeLists、脚本、文档、JSON 结果/fingerprint、小型日志及
  profiler TOML/INI。构建树、可执行文件、对象、缓存和大型 dump 不加入 Git，
  **不删除本地副本**。生成物有留痕不等于能逐字节重建旧二进制。
- 末期研究会话没有在本次被重新启动；本交接不承诺后台继续运行。
- 之前已获用户确认的 AGENTS.md 紧急暂停段落删除一并归档，不改动其他治理规则。
- 正式失败/未完成证据与最终 19.48 bundle 分开保存，不据归档 commit 晋升。
