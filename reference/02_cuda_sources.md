# CUDA/CUTLASS/推理框架参考资料

这些项目可提供算法、数值处理、数据流和实现方法参考，并非只能参考结构。
CUDA/CUTLASS 源码通常不能未经适配就在 AscendC 编译运行；但其中的算法和舍入
规则可以经对应实现复用。不能从平台名称推断数值必然不同，也不能假定必然相同。
Triton-Ascend 面向昇腾，不能与仅针对 CUDA 的实现混为一谈。

## vLLM 动态 INT8 量化

- 源文件搜索入口：<https://github.com/vllm-project/vllm/search?q=dynamic_scaled_int8_quant_kernel&type=code>
- 历史实现路径：`csrc/quantization/compressed_tensors/int8_quant_kernels.cu`
  （见下方 PR；本次访问 main 分支该文件返回 404，不能作为当前路径）。
- 向量化优化 PR：<https://github.com/vllm-project/vllm/pull/19233>

本次核验的是 PR #19233 的历史 diff，其中包含动态 INT8 kernel 和
`VEC_SIZE=16` 向量化改动；不能据此断言当前所有 vLLM 实现均使用固定 16。
可研究 amax 归约、批量访问、尾块和 scale 复用；AscendC 的最佳向量长度、
对齐与分块需要重新测量。

CUDA 数值转换可以作为语义对照；是否与当前目标一致，需要比较舍入模式、
除法/乘倒数、溢出/饱和和特殊值行为。对于同一组有限非负的 ReLU 后数据，
absmax 与 max 相同；不能把这一等价性扩大到 ReLU 前的一般有符号输入。

## CUTLASS Epilogue

- vLLM CUTLASS epilogue 文档：<https://github.com/vllm-project/vllm/blob/main/csrc/quantization/w8a8/cutlass/Epilogues.md>
- CUTLASS epilogue 目录：<https://github.com/NVIDIA/cutlass/tree/main/include/cutlass/epilogue>
- CUTLASS fused GEMM examples：<https://github.com/NVIDIA/cutlass/tree/main/examples>

可研究 accumulator 到 dequant、激活、输出转换的融合，以及 tile 内行/列
scale 广播。本次列出的是项目/目录入口，未核验某个 SM120 文件确实支持本算子
所需的完整行归约和 INT8 输出。

动态 scale 产生了“完整行统计先于最终量化”的数据依赖，但不必然要求两个
kernel 或两遍 GM 读取。整行可驻留片上、归约后继续处理，或重算/多阶段实现
均可研究；跨 N tile 的 epilogue 则需说明完整行统计如何交换。

## TensorRT-LLM / row-column scale

- `epilogue_per_row_per_col_scale.h`：<https://github.com/NVIDIA/TensorRT-LLM/blob/main/cpp/tensorrt_llm/cutlass_extensions/include/cutlass_extensions/epilogue/threadblock/epilogue_per_row_per_col_scale.h>

本次已访问该文件，可研究 per-row/per-column scale 的 broadcast 和 epilogue
组织。题面参考采用 `RN32(RN32(float(acc) * rowScale) * colScale)` 的分步形式；
预乘 scale、换序或融合可能改变中间舍入，但不等于必然违反验收要求。
应区分“与参考逐位相同”与“输出满足正式容差”，按实际目标验证。

## torch-int / CUTLASS ReLU epilogue

- 源码：<https://github.com/Guangxuan-Xiao/torch-int/blob/main/torch_int/kernels/linear.cu>

可借鉴 `linear_relu_a8_w8_b8_o8` 的 GEMM + ReLU 融合边界和输出 epilogue。
它不解决动态 row scale，适合研究 Cube 输出如何直接进入 Vector/epilogue。

## PyTorch RowwiseScaledMM 与其他项目

- PyTorch CUDA rowwise scaled MM 搜索入口：<https://github.com/pytorch/pytorch/search?q=RowwiseScaledMM.cu&type=code>
- TensorRT-LLM epilogue 目录：<https://github.com/NVIDIA/TensorRT-LLM/tree/main/cpp/tensorrt_llm/cutlass_extensions/epilogue>
- FBGEMM：<https://github.com/pytorch/FBGEMM>
- DeepGEMM：<https://github.com/deepseek-ai/DeepGEMM>
- FlashInfer：<https://github.com/flashinfer-ai/flashinfer>
- Triton matmul tutorial：<https://github.com/triton-lang/triton/tree/main/python/tutorials>

这些是扩展检索入口，本次未逐项审查具体实现。可研究广播、向量化、归约、
布局和流水等方法，不限于上述三类。FP8/FP4/blockwise quant 的数据格式与
分组语义不能自动当作本算子的 INT8 定义；部分数值算法经证明和适配仍可能复用。
