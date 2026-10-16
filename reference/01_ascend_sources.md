# Ascend/CANN 参考资料

## 1. GroupedMatmulQuantMixCore（建议阅读，无收益排序结论）

- 源码：<https://gitee.com/ascend/cann-ops-adv/blob/58e37b812de0069ab9191717945cd2afd61f653d/src/transformer/grouped_matmul/grouped_matmul_quant_mixcore.h>
- 设计文档：<https://gitee.com/ascend/cann-ops-adv/blob/master/docs/GroupedMatmul.md>

重点函数/概念：

| 函数或结构 | 当前工程的参考点 |
|---|---|
| `MMCompute` | Cube tile、workspace offset、M/N 尾块处理 |
| `VectorCompute` | Cube 完成后 Vector 消费 tile 的时序 |
| `ComputeDequantAndActivate` | int32 → FP32、scale 广播、激活、输出流水 |
| `ActivationCompute` | Vector 侧激活的计算组织 |
| `DataCopyPerTokenScaleAndBrcb` | 行 scale 加载与广播 |
| `VectorTilingCalc` | Vector 分块以及 UB 容量、对齐约束的处理 |
| `CrossCoreWaitFlag` / `CrossCoreSetFlag` | AIC/AIV 生产者-消费者同步和流水深度 |

可对照以下三个问题；它们是研究建议，不是已经实现或验证的收益：

1. Cube 每完成一个 tile 后是否立即通知 Vector，而不是等待完整矩阵；
2. workspace 是否只保存无法直接消费的中间结果，避免重复 GM 往返；
3. per-token/per-channel scale 是否在 UB 中一次加载并复用。

## 2. FFNQuant

- 源码：<https://gitee.com/ascend/cann-ops-adv/blob/c47f5497485cf3c47f09fb8eb592dfe0a75968a9/src/transformer/ffn/ffn_quant.h>
- 调度入口：<https://gitee.com/ascend/cann-ops-adv/blob/c47f5497485cf3c47f09fb8eb592dfe0a75968a9/src/transformer/ffn/ffn.cpp>

重点查看 `QuantCompute`、`CastCompute`、`DequantDataCopy`、
`CopyFromWorkspaceMM1`、`MM2Compute` 和 `ControlMM2`。本次已在固定 commit
源码中确认这些函数存在。其量化参数与当前逐行动态 scale 的对应关系仍需核对；
函数名或融合结构相似，不足以说明输入输出及数值行为相同，也不排除经适配复用。

## 3. DynamicQuant / DynamicQuantV2

- CANN 高阶算子库入口：<https://gitcode.com/cann/ops-nn>
- 文档检索入口：<https://www.hiascend.com/document>（检索 DynamicQuant / DynamicQuantV2，选择对应版本）。
- DynamicQuant 相关公开实现/讨论入口：<https://gitee.com/ascend/cann-ops-adv>

以上只是项目/文档检索入口，本次未定位并核验对应版本的具体 DynamicQuant/V2
实现；不能据此声称其已实现下列全部功能。后续可检查 `op_host` / `op_kernel`：

- 跨 tile 的 row max 归约；
- zero row 与 tail mask；
- scale 与 inverse-scale 的广播；
- 向量 Cast、Clamp、写回的批量化。

若所选实现采用对称 absmax 量化：对同一组有限非负激活值，absmax 与 max
相同；但对 ReLU 之前的一般有符号输入，absmax 通常不等于 ReLU 后的 max。
还需核对是否含 smooth scale、非对称量化、zero row 特殊处理和不同舍入方式。

## 4. AscendC API 与样例

- AscendC 高阶 API：<https://gitee.com/ascend/ascendc-api-adv>
- Triton-Ascend CV Fusion 指南：<https://github.com/Ascend/triton-ascend/blob/main/docs/en/programming_guide/cv_fusion_operator.md>
- Triton-Ascend 编程指南：<https://github.com/Ascend/triton-ascend/tree/main/docs/en/programming_guide>
- GatherMask / CreateVecIndex：本地 CANN 9.1.0 的
  `asc/include/basic_api/kernel_operator_vec_gather_mask_intf.h` 和
  `asc/include/basic_api/kernel_operator_vec_createvecindex_intf.h`。
  已确认前者含 tensor pattern 与 `uint64_t& rsvdCnt` 参数，后者含索引生成接口；
  声明存在不等于特定芯片、数据类型和模式均已验证。

可实验的方案（尚未实现完整原型）：

```text
CreateVecIndex 生成原始 lane 索引
Compare/Compares → 适配筛选 mask → GatherMask 分别压缩值和索引
→ 精确修正 → 通过原始索引写回
```

CreateVecIndex 本身不会恢复压缩前索引，也不执行 scatter。Compare 的输出
能否直接作 GatherMask pattern、不同位宽的值/索引是否使用相同筛选顺序、计数
返回、写回方式及 dav-2201 支持情况均待验证。筛选前还需证明风险判据覆盖所有
可能误舍入 lane（见 `../ev/QUANT_ERROR_BOUND.md`）；mask 布局正确本身不足以
证明量化正确，也不能证明该路径更快。

## 5. 其他 AscendC 方向

- QuantBatchMatmulV3/V4：可从 CANN 算子库检索相应版本；当前仅提供项目入口，
  未核验具体实现路径：<https://gitcode.com/cann/ops-nn>。
- MatMul/LeakyReLU 样例：从配套 CANN AscendC examples 中搜索
  `MatmulLeakyReluCustom`、`simple_matmulleakyrelu`、`mmad_kernellaunch`。
- Fixpipe：从本地 CANN 9.1.0 headers/examples 搜索 `Fixpipe` 和
  `SetFixpipe`。支持的格式转换、量化和激活能力依产品、模式和版本而定。
  使用预设 scale 的转换不能独自求出尚未得到的完整行 max；但不排除把 Fixpipe
  与归约、缓存或多阶段方案组合。当前未验证本算子适用的具体配置。
