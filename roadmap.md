# QuantMatmulReluQuant：文件导航与后续路线

更新时间：2026-10-16。本文按用途列出源码和文档；大量自动生成的输入、输出、编译缓存与 CAModel dump 按目录/命名规则归类，不逐个枚举。

## 总目标

在题目 15 个测试点全部通过的前提下，以题目实际计时口径最小化端到端用时，
最终达到全体候选实现中的最优平均性能。参考资料和实验必须服务于这个目标：
先做瓶颈归因，再做可回退的候选；正确性、设备语义和正式计时口径未确认时，
不以单点 CAModel 加速替代最终结论。详细参考入口见 [`reference/`](reference/README.md)。

## 1. 从哪里开始看

1. **题目与约束**：[ques/quantmatmulreluquant.md](ques/quantmatmulreluquant.md)。
2. **当前开发入口**：[kernel.asc](kernel.asc)，由根 `main.asc` 和实验程序共同引用。
3. **保留版本**：`op/` 下的三个 kernel，不覆盖、不当作临时实验文件使用。
4. **现有评测与风险**：先看 `ev/`，再看 `optimization/` 中的历史实验。
5. **复现测试**：使用 `optimization/benchmark.py`；单点示例入口为根 `main.asc`。
6. **外部实现参考**：看 `reference/README.md`，再按 AscendC → DynamicQuant → CUDA epilogue 顺序阅读。

### 当前状态（避免混淆）

- 根 `kernel.asc` 已将 `QUANT_MASK_FAST_PATH` 默认值改为 **0**：保留向量 hint，但由 exact helper 认证/修正，不能再称它与 v3 逐字相同。
- `op/kernel_v3.asc` 是开启 boundary-mask 快路径时的冻结快照；用户外部评测曾 15/15 通过，但这不是所有 FP32 输入的正确性证明。
- `op/kernel.asc` 是历史对照基线，`op/kernel_v2.asc` 是早期候选快照，均保留不动。
- `bench_vector` 仅消融量化精确校正；**仍包含矩阵乘等整个算子阶段**，不是已完成的独立纯 Vector 微基准，也不是可提交的正确实现。
- `optimization/vector_error_distribution.py` 是宿主误差模型，不是设备指令误差分布或设备误差上界证明。
- 新的保守版本已编译；`optimization/safe_regression.log` 本轮 11 个指定 case 均完成，mismatch=0 且 scale_ok=true。详细周期对比和限制见 `report.md`；这不是官方 15/15 或 score 证据。
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
| `gitlabcann/userid.txt` | 默认 CANNJudge 用户 ID | 提交和排行榜命令自动读取；可用 `--user-id` 覆盖 |
| `team.txt` | 默认排行榜搜索队伍名称 | 当前值为 `西西里 的队伍`；排行榜命令可用 `--query` 覆盖 |
| `gitlabcann/cookie` | 登录会话 Cookie | 敏感凭证，不应分享或提交到版本库 |
| `gitlabcann/__pycache__/` | Python 自动缓存 | 非源码 |

注意：该工具向 CANNJudge 提交，不是 GitLab OAuth 客户端；实际上传文件以服务端
题目模板中的可编辑文件为准。已用真实账号完成一次提交与结果/排行榜查询联调，
结果与提交 ID 见 `report.md`；Cookie 仍为敏感凭证。

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
- 题面 CPU 参考使用 **INT32 matmul**，但本地 `scripts/QuantMatmulReluQuant.py` 和 `optimization/benchmark.py` 当前使用 FP32 matmul golden。大 K、累加溢出/转换边界必须独立核对，不能把本地通过等同于严格题意通过。
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
| `optimization/test_points.json` | 本地 15 点及 profile 说明；runner 的 `SUITE` 另有一份定义，修改用例时需同步 |
| `optimization/check_quant.py` | 提取根 kernel exact helper，在宿主 C++ 上测试随机 hint、半整数边界和 IEEE mask 模型 |
| `optimization/vector_error_distribution.py` | 假设 reciprocal 误差预算的宿主扰动实验；不能代替设备 reciprocal 精度保证 |
| `optimization/baseline/kernel.asc` | 更早的原始源码对照，不是 `op/kernel.asc` |

### variant 对照

| variant / 可执行文件 | 对应实现 |
|---|---|
| `baseline` / `bench_baseline` | `optimization/baseline/kernel.asc` |
| `prior` / `bench_prior` | `op/kernel.asc` |
| `v2` / `bench_v2` | `op/kernel_v2.asc` |
| `v3` / `bench_v3` | `op/kernel_v3.asc` |
| `optimized` / `bench_optimized` | 当前根 `kernel.asc`，默认 mask 快路径关闭 |
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

`result.json` 中关注 `mismatches`、`scale_ok`、`scale_max_diff`、`binary_sha256`、`task_cycles`。宿主仿真墙钟时间不代表 NPU 延迟。

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

CAModel 回归应串行执行，避免与正在运行的任务共用相同结果目录。`--resume` 只复用 binary hash 匹配的结果；历史日志仍需检查其源码状态与测量口径。

## 9. 后续 roadmap（按优先级）

1. **对齐正式计分口径和题目语义**：核对本地 FP32 matmul golden 与题面 INT32 累加差异、正式 CANN 版本、H2D/Kernel/D2H 计时范围、INT32 溢出假设、非有限输入和超小 scale 行为；独立生成标准参考，不改写历史基线。
2. **建立最优用时基线**：收齐 15 点、极端 INT8、零行、负 scale、tail、tiny scale、K=65536/131072、大 M 与多核测试；对 prior、v3、safe kernel 记录源码/二进制 hash、端到端时间和 CAModel 分阶段指标。
3. **优先减少 Cube/Vector 协同和 GM 流量**：按 `reference/01_ascend_sources.md` 对照 GroupedMatmulQuantMixCore/FFNQuant，验证 tile 级 CrossCore 流水、workspace 生命周期、scale 广播和 UB 复用。
4. **完成真正独立的设备诊断**：增加固定 workspace 的 Vector-only 微基准、Cube-only 对照、fallback/scale 分支统计，以及 Compare mask 位序、GatherMask 压缩布局和 Select 行为测试。计数版本不得用作正式性能结果。
5. **降低精确校正成本**：按 `reference/03_current_kernel_mapping.md` 制作独立候选，研究先生成原始索引、再用风险 mask 一致筛选值和索引、精确校正后按索引写回；风险判据本身需验证，不能只验证 GatherMask 布局。目标是减少逐元素 `GetValue/SetValue`，覆盖半整数与非精确倒数边界后再测 CAModel。
6. **按 shape 做专用调优**：小形状优化启动和同步，中等形状优化 UB/Vector pipeline，大形状优化 Cube 利用率、M/N 负载和 GM 带宽；按题面逐点得分评估，不能用平均耗时直接代替平均得分。
7. **最后考虑 row-max 跨 N 重构**：只有 profile 证明收益明确时，才做 partial row max、跨核同步和第二阶段量化；不能用局部 max 替代完整 row max。
8. **合入门槛与回退**：全部正式测试点通过、INT8 采用当前保守的完全一致策略、scale 合格、设备语义有证据，并且按正式规则评估后性能收益足以抵消回归风险，才替换根版本；否则保留 `op/kernel.asc` 历史基线和所有候选快照。
