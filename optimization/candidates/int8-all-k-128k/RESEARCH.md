# int8-all-k-128k

## 目标

所有 K 使用 INT8 Cube；将单个 INT32 Cube chunk 放宽为 `SAFE_ACCUM_K=131072`，
专门观察硬件在潜在 `2^31` 边界附近的行为。超过该长度仍按 chunk 使用 GM atomic 累加。

## 身份

- 源码 SHA256：`e74dbd3c1a045820df23a919cd6f72c6b65639dba489bccce3d01f7f962b2211`
- 独立构建二进制：`/tmp/opencode/int8-all-k-128k-project/build/quant_matmul_relu_quant_custom`
- 二进制 SHA256：`4aeaaec47d2accfb5f31f80e6b766ded6571ea99c1c8a7901467fe1666150def`

## 验证

- CANN 9.1.0 / Ascend910B1 CAModel，严格 INT32 golden。
- `1x1x65536`、`1x1x65537`、`1x1x131072`、`1x1x131073`，boundary 输入：
  `int32_mismatches=0`、`int32_scale_ok=true`，均完成。
- task cycles 依次为 `61652, 62969, 101149, 105838`。
- 宿主 `optimization/int32_golden.py` 六组边界回归通过。

## 风险/状态

`1x1` boundary 全为 `127*(-128)`，ReLU 后全零，对累加正确性的辨别力很弱。
真正恰达 `2^31` 的正向边界是 `(-128)*(-128)*131072`，不是 `127*127`；
必须补做极值/交错输入后
才能判断 128k chunk 是否数值安全。这是隔离候选，未替换根实现、未正式提交。
