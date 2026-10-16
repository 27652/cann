# QuantMatmulReluQuant 研究与决策记录

更新时间：2026-10-16

## 当前历史最佳有效结果（已复核）

- 提交 ID：`6ad2872c193e507d8ed198c9`
- 赛事：`op_challenge_hangxia_prelim`；赛事 ID：`6a9a94b9bf41025d6012d4dd`
- 题目：`quantmatmulreluquant`；题目 ID：`6a9a9ec4bf41025d6014adbe`
- 官方状态：`Pass`；结果包含 15 个 testcase，15/15 为 `Pass`，每项 `precision_ratio=1`
- 绑定同一提交的排行榜记录：`rank=232`、`score=11.67`，`submission_id` 与上述提交一致
- 原始结果存储：`/tmp/opencode/kernel-existing-submission-result.json`
- 排行榜快照：`/tmp/opencode/cannjudge-ranking-team-file.json`
- 证据核查：2026-10-16 静态读取 JSON 结构、15 条结果状态、提交 ID 和排行绑定；未读取 Cookie，未执行登录、提交或结果查询。

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

上述是目前已确认的历史有效官方结果；当前根不是该提交的完全相同源码版本。本轮没有产生新的提交。

## 证据与当前候选可复原性

- 元数据和提交文件 hash 清单：`evidence/formal/manifest.txt`、`evidence/formal/submission-files.sha256`。
- 该目录不保存 Cookie 或原始 API 回包；原始结果仍在 `/tmp/opencode/kernel-existing-submission-result.json`，排行快照仍在 `/tmp/opencode/cannjudge-ranking-team-file.json`。
- 历史正式提交的 8 个 editable 文件均有内容 hash；其中只有 `kernel.asc` 与当前本地文件不一致。因此历史提交可由清单和原始结果中的文件内容恢复，但当前候选不能声称是该正式提交的可复原副本。
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
- 本轮 benchmark 的 golden 路径仍使用 FP32 matmul；题面参考是 INT32 matmul。
  因此大 K 和 INT32 转 FP32 边界仍未由这轮回归证明。
- 该回归覆盖的是本地指定的 11 个 case，不是官方 15 个输入点；不能写成正式
  15/15 证据。

## 决策

保留当前根实现和回归日志，不修改冻结的 `op/kernel*.asc`。本轮结果支持继续
分析 optimized 的大形状收益，但不足以仅凭 CAModel 结果自动替换或宣称 score
提升。下一次正式提交前，应记录服务端模板返回的 editable 文件清单和每个内容
hash；不得假设实际上传文件只有 `kernel.asc`。正式晋升仍以同一 submission_id
对应的 15/15 和 score 作为唯一依据。

## 下一步

1. 复核 case 14 的 `scale_ok` 判定与 `scale_max_diff` 的关系，避免宽松容差掩盖
   yScale 问题。
2. 在不覆盖冻结文件的前提下，补充 INT32 matmul 语义的大 K/极值检查。
3. 需要比较官方 score 时，等待平台限流解除后只提交已核对的 `kernel.asc`，并
   保存提交 ID、上传源码 hash、15/15 状态、score 和排行榜快照。
