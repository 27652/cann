# 保守量化误差界与部署门槛

令 x=a/b，a>=0，b>0，目标是 RNE_integer(RN32(x))，而非直接对真实 x
做整数 RNE。设 reciprocal r 满足 |br-1|<=rho，乘法为正确舍入 FP32，
u=2^-24。对正常数、没有 overflow 的计算：

    |RN32(a*r)-x| <= x*(rho+u+rho*u) + 2^-150
    |RN32(x)-x| <= u*x + 2^-150

故两种 quotient 的距离至多：

    E = x*(rho+2*u+rho*u) + 2^-149。

只在已证明 x<=128 的行适用固定界。距离 approximate quotient 最近的半整数
大于 E（再计入距离计算的舍入误差）时，两次整数 RNE 必定相同；否则必须
执行 exact helper。恰在半整数的 tie 必须 fallback。

例如 rho=2^-14 时 E<0.00783，阈值 1/64=0.015625 留有充足余量（距离
计算在 [0,128] 内，即使额外留 2^-15 的余量仍足够）。但这不是当前设备
reciprocal 的 rho 证明，不能据此直接开启快路径。

特别地，v3 的 1/1024 阈值在 rho=2^-14 的假设下**没有保证**。
宿主测试的 perturbation 反例说明为什么不可仅从随机零错误推断设备误差界。
完整部署还必须确认：

* scalar reciprocal 的编译 lowering 及文档精度界；
* vector multiply、Cast RNE 和 subnormal/FTZ 行为；
* rowMax / 127 的精度及 quotient 上界；
* 非有限值、scale underflow、subnormal activation 的处理；
* Compare 输出 mask 位布局。

目前无法从已查到的公开头文件给出上述设备精度保证。根 kernel 因而默认
`QUANT_MASK_FAST_PATH=0`，所有有效元素都由 exact helper 认证/修正。
v3 保持冻结，vector-only 仅为消融。历史 op 基线保留不动。
