# int8-all-k-safe

## 目标

取消 `K >= 65536` 的 INT8→FP32 转换和 FP32 Cube 路径；所有 K 使用 INT8 Cube，
并以 `SAFE_ACCUM_K=65536` 分块。跨 chunk 的 INT32 GM 累加仍使用现有
`atomicAdd` 机制，保证 chunk 内不超过已采用的安全上限。

## 身份

- 源码 SHA256：`25c4eae25f4ca44e67ff794777274284c93418860c73f28d031daaaed226a855`
- 独立构建二进制：`/tmp/opencode/int8-all-k-safe-project/build/quant_matmul_relu_quant_custom`
- 二进制 SHA256：`43950a307ea5ff5c75b541d354a98dcafbf2cb34568868d11687134b1cd0f469`

## 验证

- CANN 9.1.0 / Ascend910B1 CAModel，严格 INT32 golden。
- `1x1x65536`、`1x1x65537`、`1x1x131072`、`1x1x131073`，boundary 输入：
  `int32_mismatches=0`、`int32_scale_ok=true`，均完成。
- task cycles 依次为 `61652, 66262, 104472, 108773`。
- 宿主 `optimization/int32_golden.py` 六组边界回归通过。

## 风险/状态

这是隔离候选，未替换根 `kernel.asc`，未取得正式 score。上述 CAModel 数据只覆盖
`1x1` boundary。该输入全为 `127*(-128)`，ReLU 后全零，不能证明 chunk 寻址或
累加正确；极值正累加、较大 M/N、尾块、跨核 ownership 和服务端性能仍待验证。
