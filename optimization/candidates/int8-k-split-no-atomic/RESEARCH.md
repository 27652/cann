# int8-k-split-no-atomic

## 目标

取消跨核 chunk 的 atomic 写入：每个 K chunk 写入独立的 aligned GM plane，Vector
owner 串行读取所有 planes 并做 INT32 累加。该版本以 65536 为 chunk 上限，属于结构
实验，不假设其一定快于 atomic 版本。

## 身份

- 源码 SHA256：`470bd85a029274c73ff7476037f79bae87dbcd4aaf1695a90863c2aaa629534b`
- 独立构建二进制：`/tmp/opencode/int8-k-split-no-atomic-project/build/quant_matmul_relu_quant_custom`
- 二进制 SHA256：`75ab1437dda4be0cb8dde588f91aabab133ca7929f4456d8cad04ce5e30a2b03`

## 验证

- CANN 9.1.0 / Ascend910B1 CAModel，严格 INT32 golden。
- `1x1x65536`、`1x1x65537` 已完成，均 `int32_mismatches=0`、`int32_scale_ok=true`。
- task cycles 为 `62196`、`66794`。
- 后续两点在本轮 CAModel 时间预算内未完成；宿主六组 golden 通过。

## 风险/状态

增加了按 chunk 数量线性增长的 INT32 workspace 和 Vector 读取/累加成本；还未覆盖
大 M/N、极值、跨核和 workspace 上限。仅保留为候选，不替换根实现、未正式提交。
