# QuantMatmulReluQuant

- 来源页面：https://cannjudge.cn/public/op_challenge_hangxia_prelim/quantmatmulreluquant
- 竞赛：`op_challenge_hangxia_prelim`
- 题目：`quantmatmulreluquant`
- 题目 ID：`6a9a9ec4bf41025d6014adbe`
- 保存时间：2026-10-16

# QuantMatmulReluQuant算子

## 一、赛题背景

在大语言模型（LLM）推理场景中，矩阵乘法是计算量最大的操作。为降低显存占用和计算延迟，业界广泛采用 INT8 量化技术。在典型的 INT8 量化推理前向流程中，单层计算需依次经历"量化矩阵乘 → 激活函数 → 动态再量化"三个阶段，分别对应不同的 Kernel。将这三个阶段融合为单个算子，可显著减少 kernel launch 开销和中间数据搬运，是提升推理吞吐的关键优化方向。

## 二、算子功能描述

实现的 QuantMatmulReluQuant 算子需完成以下三阶段计算的融合：

实现如下：

```
Step 1: matmulOut = cast_fp32(x1 @ x2) * x1Scale * x2Scale
Step 2: activationOut = relu(matmulOut)
Step 3: y, yScale = dynamic_per_token_quant(activationOut)
```

1. **INT8 量化矩阵乘**：对 INT8 输入 x1、x2 执行矩阵乘法，使用 INT32 累加，再通过 per-token 量化因子 x1Scale 和 per-channel 量化因子 x2Scale 反量化为 FLOAT32 结果。
2. **ReLU 激活**：对 FLOAT32 矩阵乘结果施加 ReLU 激活函数。
3. **动态 per-token 量化**：对 ReLU 激活后的 FLOAT32 结果，按行（M 维）计算动态量化因子，将结果量化为 INT8 输出，同时输出每行的量化因子。

## 三、核心定义与约束

### 3.1 参考算子

CPU 参考实现伪代码如下：

```python
import numpy as np

def quant_matmul_relu_quant_cpu(x1, x2, x1_scale, x2_scale):
    # x1: (M, K), x2: (N, K) 
    M, K = x1.shape
    N, K_x2 = x2.shape
    assert K == K_x2

    x2_logical = x2.T

    # 阶段一：INT8 矩阵乘 + 反量化
    matmul_out_int32 = np.matmul(x1.astype(np.int32), x2_logical.astype(np.int32))  # (M, N)
    matmul_out_fp32 = matmul_out_int32.astype(np.float32)
    matmul_out_fp32 = matmul_out_fp32 * x1_scale.reshape(M, 1)  # per-token scale
    matmul_out_fp32 = matmul_out_fp32 * x2_scale.reshape(1, N)  # per-channel scale

    # 阶段二：ReLU 激活
    activation_out = np.maximum(0.0, matmul_out_fp32)

    # 阶段三：动态 per-token 量化
    row_max = np.max(np.abs(activation_out), axis=1)  # (M,)
    y_scale = np.where(row_max > 0, row_max / 127.0, 1.0)  # (M,)

    quantized = np.rint(activation_out / y_scale.reshape(M, 1))
    y = np.clip(quantized, -128, 127).astype(np.int8)

    return y, y_scale.astype(np.float32)
```

算子行为、计算结果需与上述 CPU 参考实现完全对齐。

### 3.2 数学公式

**阶段一 — 量化矩阵乘与反量化：**
$$
\text{matmulOut}_{fp32}[m, n] = \text{cast}_{fp32}\!\left(\sum_{k=0}^{K-1} x1[m, k] \times x2[k, n]\right) \times x1Scale[m] \times x2Scale[n]
$$

- $x1$ 为 INT8 类型，形状 $(M, K)$（不转置）。
- $x2$ 为 INT8 类型，形状 $(N, K)$（转置）。
- 矩阵乘内部使用 INT32 累加，随后 `cast` 为 FLOAT32。
- $x1Scale$ 为 per-token（行级）反量化因子，FLOAT32，形状 $(M,)$。
- $x2Scale$ 为 per-channel（列级）反量化因子，FLOAT32，形状 $(N,)$。

**阶段二 — ReLU 激活：**
$$
\text{activationOut}[m, n] = \max\!\left(0,\ \text{matmulOut}[m, n]\right)
$$

**阶段三 — 动态 per-token 量化：**

对 activationOut 的每一行（沿 N 轴），执行对称量化：

Step 1：计算每行最大绝对值
$$
\text{rowMax}[m] = \max_{n=0}^{N-1}\left|\text{activationOut}[m, n]\right|
$$

Step 2：计算量化因子
$$
\text{yScale}[m] = \begin{cases}
\dfrac{\text{rowMax}[m]}{127.0}, & \text{if } \text{rowMax}[m] > 0 \\
1.0, & \text{if } \text{rowMax}[m] = 0
\end{cases}
$$

Step 3：量化并截断
$$
y[m, n] = \text{clamp}\!\left(\text{round}\!\left(\frac{\text{activationOut}[m, n]}{\text{yScale}[m]}\right),\ -128,\ 127\right)
$$

- `round` 采用就近偶数舍入（round-half-to-even，即 `rint` 模式）。
- `clamp` 将结果限制在 INT8 表示范围 $[-128, 127]$ 内。

### 3.3 输入输出与属性总览

| 类型         | 参数名  | 类型   | 维度形状 | 支持数据类型 | 数据格式 | 备注                                            |
| ------------ | ------- | ------ | -------- | ------------ | -------- | ----------------------------------------------- |
| INPUT(必选)  | x1      | tensor | $(M, K)$ | INT8         | ND       | 矩阵乘左矩阵（激活），固定不转置                |
| INPUT(必选)  | x2      | tensor | $(N, K)$ | INT8         | ND       | 矩阵乘右矩阵（权重，已转置，逻辑形状 $(K, N)$） |
| INPUT(必选)  | x1Scale | tensor | $(M,)$   | FLOAT32      | ND       | per-token 反量化因子                            |
| INPUT(必选)  | x2Scale | tensor | $(N,)$   | FLOAT32      | ND       | per-channel 反量化因子                          |
| OUTPUT(输出) | y       | tensor | $(M, N)$ | INT8         | ND       | 动态量化后的最终结果                            |
| OUTPUT(输出) | yScale  | tensor | $(M,)$   | FLOAT32      | ND       | 每行的动态量化因子                              |

### 3.4 关键输入约束

- **维度取值范围(均为正整数)**:
  - $M \geq 1$，$N \geq 1$，$K \geq 1$。
  - 输入 x1、x2 支持 **2 维**。

- **数据类型约束**:
  - x1 和 x2 的数据类型必须均为 **INT8**。
  - x1Scale 和 x2Scale 的数据类型必须均为 **FLOAT32**。

- **其他约束**:
  - 不支持空 Tensor。
  - 仅支持连续 Tensor。

- **数值取值约束**: 输入张量的数值取值范围不超出各自数据类型的原生表达范围

### 3.5 核心属性说明

无属性参数。x1 固定为不转置（形状 $(M, K)$），x2 固定为已转置（形状 $(N, K)$，逻辑形状 $(K, N)$）。

### 3.6 输出严格要求

- **形状约束**:
  - 输出 `y` 的 shape 为 $(M, N)$。
  - 输出 `yScale` 的 shape 为 $(M,)$。

- **类型约束**:
  - `y` 数据类型为 **INT8**。
  - `yScale` 数据类型为 **FLOAT32**。

- **数值等价**: 输出结果应与 CPU 参考实现（quant_matmul + relu + dynamic_quant）的计算结果在精度允许范围内一致

### 3.7 特殊值处理规则

- **rowMax = 0 处理**: 当 rowMax[m] 为 0 时（整行激活结果均为 0），yScale[m] 输出为 1.0（而非 0 或 inf），对应行的 y 输出全为 0，避免除零导致 NaN。
- **累加溢出保护**: INT32 累加结果反量化为 FLOAT32 时，需注意大 K 值下累加结果溢出风险；INT8×INT8 累加结果在 INT32 范围内，但 cast 到 FLOAT32 后需保证精度不丢失。

## 四、规则要求

1. **数值一致性规则**: 给定相同的输入，算子多次执行结果应完全一致（确定性算子，不含随机性）

2. **舍入与截断规则**:
   - 量化除法后采用就近偶数舍入（`rint` 模式），即 0.5 向最近的偶数舍入。
   - 舍入后 clamp 到 INT8 表示范围 $[-128, 127]$。
   - 截断顺序：先 round，后 clamp，不可调换。

3. **性能要求**：在保证数值精度和正确性的前提下，优化计算性能，充分利用 NPU 硬件特性：
   - 支持向量化计算，合理利用 Cube 与 Vector 计算单元
   - 优化内存访问模式，减少 GM 与 UB 之间的数据搬运
   - 合理利用多核并行，沿 M 维和/或 N 维分配任务到不同核
   - 鼓励使用 Double Buffer / Ping-Pong 机制实现 Cube 与 Vector 的流水重叠
   - 性能指标：算子端到端执行时间（含 H2D 搬运 + Kernel 执行 + D2H 搬运）
   - 性能基线：拆分实现（先调用 `aclnnQuantBatchMatmulV3`，再调用 `aclnnRelu`，最后调用自定义量化 Kernel）的总耗时；评分按融合实现相比拆分基线的加速比，加速比越高得分越高
   - 性能数据采集：使用 `msprof` 工具采集算子性能数据，关注 Task Duration、Cube 利用率、Vector 利用率、MTE2/MTE3 带宽利用率
   - 代码质量：正确使用 AscendC API（Matmul、Vector、Buffer 管理）；Tiling 策略合理（多核负载均衡、UB 内存不溢出）；流水线设计（Cube-Vector 重叠、Double Buffer）；代码可读性与注释完整性

## 五、精度判断规则

精度要求：计算结果需满足以下精度误差要求：

- float32：相对误差 < 1e-4，绝对误差 < 1e-4（双万分之一精度）
- float16、bfloat16：相对误差 < 1e-3，绝对误差 < 1e-3（双千分之一精度）
- int32：要求计算结果完全准确，无误差

## 六、得分规则
- 本次比赛共15个测试点，所有case点精度全部通过才会计分。
- 每个测试点单独计分，逻辑如下（T为最优性能，t为当前提交性能）：
$$
\frac{100}{1+\log_{1.5}\frac{t}{T}}
$$
- 排行榜显示的最终分数为所有case得分的均值。若得分计算一致，则以提交时间进行排序，提交越早，排名越高。

## 七、示例说明

**示例 1**: 基础计算

- 输入 x1: shape=(2, 4), dtype=INT8, 值为 [[1, 2, 3, 4], [5, 6, 7, 8]]
- 输入 x2: shape=(3, 4), dtype=INT8（已转置，逻辑形状为 (4, 3)）, 值为 [[1, 4, 7, 10], [2, 5, 8, 11], [3, 6, 9, 12]]
- 输入 x1Scale: shape=(2,), dtype=FLOAT32, 值为 [0.01, 0.01]
- 输入 x2Scale: shape=(3,), dtype=FLOAT32, 值为 [0.1, 0.1, 0.1]
- 计算过程:
  1. INT32 矩阵乘结果：[[70, 80, 90], [158, 184, 210]]
  2. 反量化后 matmulOut：[[0.07, 0.08, 0.09], [0.158, 0.184, 0.21]]
  3. ReLU 激活后（所有值均为正，结果不变）：[[0.07, 0.08, 0.09], [0.158, 0.184, 0.21]]
  4. rowMax ≈ [0.09, 0.21]，yScale ≈ [0.000709, 0.001654]
  5. 量化后 y（INT8）约为 [[99, 113, 127], [96, 111, 127]]
- 输出 y: shape=(2, 3), yScale: shape=(2,)
- 结果解释: 标准 INT8 量化矩阵乘 + ReLU + 动态量化流程

**示例 2**: 含负值（ReLU 截断）

- 输入 x1: shape=(2, 4), dtype=INT8, 值为 [[1, 2, 3, 4], [-5, -6, -7, -8]]
- 输入 x2: shape=(3, 4), dtype=INT8（已转置）, 值为 [[1, 4, 7, 10], [2, 5, 8, 11], [3, 6, 9, 12]]
- 输入 x1Scale: shape=(2,), dtype=FLOAT32, 值为 [0.01, 0.01]
- 输入 x2Scale: shape=(3,), dtype=FLOAT32, 值为 [0.1, 0.1, 0.1]
- 计算过程:
  1. INT32 矩阵乘结果：[[70, 80, 90], [-158, -184, -210]]
  2. 反量化后 matmulOut：[[0.07, 0.08, 0.09], [-0.158, -0.184, -0.21]]
  3. ReLU 激活后：[[0.07, 0.08, 0.09], [0, 0, 0]]
  4. rowMax ≈ [0.09, 0]，yScale ≈ [0.000709, 1.0]
  5. 量化后 y（INT8）约为 [[99, 113, 127], [0, 0, 0]]
- 输出 y: shape=(2, 3), yScale: shape=(2,)
- 结果解释: 第二行所有 matmulOut 值为负，ReLU 截断后全为 0，rowMax=0，yScale=1.0，y 全为 0

**示例 3**: 全零行

- 输入 x1: 某一行全为 0，使得对应行的 matmulOut 全为 0
- 结果解释: 当 rowMax[m] = 0 时，yScale[m] 输出 1.0（而非 0 或 inf），y[m, :] 全部输出 0，避免除零导致 NaN
