# QuantMatmulReluQuant 参考资料

本目录保存与当前算子相关的公开源码、文档入口和针对本工程的适用性分析。
资料中的外部事实、当前工程的观察和待验证建议分开描述。第三方实现可以作为
结构、数据流、tiling、同步和向量化的候选参考；移植到 `kernel.asc` 前仍需
检查 API、数据布局、数值语义、版本兼容性和性能。

## 阅读顺序

1. `01_ascend_sources.md`：与当前数据流较接近的 CANN/AscendC 源码和 API。
2. `02_cuda_sources.md`：CUTLASS、vLLM、TensorRT-LLM 等 CUDA 结构参考。
3. `03_current_kernel_mapping.md`：把参考资料映射到当前 kernel 的具体瓶颈。
4. `04_performance_plan.md`：以最终最优用时为目标的实验路线、验收门槛和停止条件。
5. `05_review_notes.md`：本次事实核查依据、修正项和未验证范围。

## 资料边界

- GroupedMatmulQuantMixCore、FFNQuant 和 Triton-Ascend CV Fusion 与当前问题的
  Cube/Vector 数据流较接近，因此列为可优先阅读的资料；这不是对其性能收益的
  结论。
- DynamicQuant/DynamicQuantV2、vLLM dynamic scaled INT8 可用于对照行归约、
  scale 广播和批量量化；具体量化定义需要逐项比较。
- CUTLASS、TensorRT-LLM、torch-int 可用于研究 epilogue、行列 scale 和 GEMM
  数据流。它们的 API、线程模型和数值转换规则不应未经验证就视为 AscendC
  实现或当前算子的精确 RNE 依据。
- 当前题目的 ReLU 后行最大值、零行 scale=1、INT8 舍入和
  `x1Scale[row] * x2Scale[col]` 语义，应以题面及正式评测规则为依据。本地 golden
  也需要核对题意（当前部分脚本使用 FP32 matmul，而题面参考为 INT32 matmul），
  不能将其无条件视为标准。

所有链接均为公开项目入口；项目内容可能随版本变化。使用时应记录实际查看的
tag/commit，并检查其与本地 CANN 版本的兼容性；不应默认认为仓库当前版本就是
本地环境的对应实现。
