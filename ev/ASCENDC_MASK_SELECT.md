# AscendC mask / Compare / Select 评估

环境：CANN 9.1.0，`dav-2201`。

## 已确认的接口

头文件：

```text
.../asc/include/basic_api/kernel_operator_vec_cmpsel_intf.h
```

2201 提供以下 Level-2 接口：

```cpp
Compares(dst, src0, scalar, CMPMODE, uint32_t count);
Select(dst, selMask, src0, src1, SELMODE, uint32_t count);
Select(dst, selMask, src0, scalar, SELMODE, uint32_t count);
```

也提供 Level-0 的 `uint64_t mask` / `uint64_t mask[]` 和 repeat 参数版本。
`Select` 的 mask tensor 类型可为 `uint8_t`，但语义是每个 lane 选择 src0 或
src1；它不是压缩/stream-compaction 指令。`Compares` 输出的是 mask tensor，
不是可移植地保证按 32 lane 排列的 `uint32_t` 数组接口。

## 对当前实现的影响

当前 v3 使用：

```cpp
Compares(boundaryMaskBuffer.Get<uint8_t>(), ..., count);
boundaryMaskBuffer.Get<uint32_t>().GetValue(base / 32);
```

编译和 CAModel 已通过，但公开头文件只保证 mask tensor 的接口语义，不在该
层保证上述 byte-to-word 位布局。因此不能把“每 32 lane 读取一个 uint32”当作
AscendC API 级证明。要正式采用，应增加专门的 Compare mask layout kernel，
用已知 lane pattern 将输出转回 GM，验证 lane 0/31/32/63 等位序。

## 可行优化

1. 用 `Compares(..., count)` 生成 lane mask；用 `Select` 直接在 UB 中选择
   approximate result 与 exact-result buffer。这样可消除逐元素结果写回，
   但 exact-result buffer 仍需被生成，不能自动减少 exact 计算。
2. 若硬件支持真实 bitmask load/store，使用 Level-0 mask 版本处理 64 lane
   块；必须同时验证 repeat stride 和 mask word 顺序。
3. 不应假设 Select 能将稀疏风险 lane 压缩成连续索引。当前 API 没有公开的
   compress/ballot-to-index 接口；若仍用 `GetValue/SetValue`，主要标量瓶颈
   只会从 mask 读取转移到 Select 前后的控制逻辑。

因此下一版实验先做 mask layout 验证和纯向量错误分布，不直接覆盖 v3。
