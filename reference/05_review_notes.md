# 参考结论审阅记录

审阅日期：2026-10-16。范围为本目录既有五份 Markdown 的结论和建议。
结论：原文并非全部准确；已修正技术错误和过度概括，并区分来源事实、工程观察
与研究建议。本记录不是对所有第三方实现或所有链接的穷尽认证。

## 主要修正

| 原表述/隐含结论 | 核查后表述 |
|---|---|
| CUDA 资料“只能”参考结构、不能参考舍入 | 数值算法与舍入规则也可研究和经适配复用；平台名称不能证明语义相同或不同。原 CUDA API 不等于 AscendC API。 |
| Triton 都不能迁移到昇腾 | 应区分后端；Triton-Ascend 本身面向昇腾，具体程序仍有接口和产品限制。 |
| absmax 与当前 max 不同 | 对同一组有限的 ReLU 后非负值，两者相同；在 ReLU 前的有符号值上通常不同。题面伪代码本身也对 activation 使用 absmax。 |
| CreateVecIndex 能恢复筛选前索引 | 它生成索引；需要预生成原始索引并与值一致地筛选，之后另行按索引写回。 |
| mask/布局/Cast 验证后就能跳过 exact | 还需要可靠的误差界或精确判据；只验证筛选功能不足以证明“安全 lane”真安全。 |
| 完整行 max 要求两个 kernel/两次 GM 扫描 | 要求统计先于最终量化，但可片上保留整行或设计其他多阶段/重算方案。 |
| 一个 Cube tile 放得下 UB 就能完成量化 | 只有取得完整行统计并保留/再次取得待量化值才足够，局部 tile 不自动满足条件。 |
| Fixpipe 不能用于动态量化 | 预设 scale 的转换不能独自计算未知 row max，但可研究与归约和多阶段方案组合。 |
| vector-only 是性能上界 | 它是非等价消融，支持定位成本，不构成最优性能的数学界。 |
| 必须所有点更快才能合入 | 这是可选择的工程策略，不是得分提高的必要条件；需按逐点非线性得分与回归风险评价。 |
| 最小化平均时间等于最大化平均得分 | 不等价；题目平均的是各点得分。公式中的 T 为该点最优时间。 |
| INT8 完全一致是已核验的正式 checker 规则 | 题面要求参考对齐与 RNE，但精度表未单列 INT8；当前完全一致是保守工程策略，不据此放宽验收。 |
| 默认优先流水/GM，且它风险低 | 这是待 profile 检验的研究顺序，不是普遍性能结论；跨核流水可能带来较高同步复杂度。 |

## 本次直接核验的材料

- `../ques/quantmatmulreluquant.md`：CPU 参考、特殊值、舍入、精度表和评分章节。
- `../kernel.asc`：默认 mask/vector-only 关闭，FindRowMax / QuantizeRow 路径。
- `../ev/QUANT_ERROR_BOUND.md`：条件性误差界及设备精度缺口。
- `../optimization/STRUCTURAL_EXPERIMENTS.md`：历史消融和缓存/tile 单点记录；
  该文的部分“当前默认”描述是历史状态，不覆盖根 kernel 当前宏值。
- `01_ascend_sources.md` 中固定 commit 的 GroupedMatmulQuantMixCore、FFNQuant
  原始源码，以及 GroupedMatmul 的 master 设计文档：本次均读取成功。
- Triton-Ascend CV Fusion 指南：本次读取成功；含片上分块、跨块同步和归约说明。
- torch-int `linear.cu`：本次读取成功，存在 `LinearCombinationRelu`。
- TensorRT-LLM 所列 per-row/per-column epilogue 文件：本次读取成功。
- vLLM PR #19233 的 GitHub files API：核验历史 diff 的动态 INT8 和 VEC_SIZE
  改动，不等同于核验当前 main 的实现。
- 本地 CANN 9.1.0 GatherMask / CreateVecIndex 接口头文件：核验声明及参数，
  未据此宣称已完成 dav-2201 设备功能或性能测试。

## 未核验项与限制

- DynamicQuant/V2、QuantBatchMatmulV3/V4 的具体对应版本源码尚未逐项定位；
  所列仓库和检索入口不算具体功能的证据。
- CUTLASS SM120、PyTorch RowwiseScaledMM 和扩展项目未逐一审阅实现；
  不对其全部能力作肯定或否定。
- 删除了此前未经核验、按目录结构拼接的 DynamicQuant/GatherMask 文档 URL；
  改用检索入口和已读取的本地头文件。
- 访问成功只证明本次能取得内容；非固定 commit 链接会变化，且不保证本地
  CANN/芯片兼容。没有运行新的 CAModel 或硬件 benchmark。
- 尚无全局最优性能证明，也没有正式 15 点完整输入及实际 checker 的实现。
