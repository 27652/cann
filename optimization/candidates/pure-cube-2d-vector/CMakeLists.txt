cmake_minimum_required(VERSION 3.16)

find_package(ASC REQUIRED)

project(quant_matmul_relu_quant_custom LANGUAGES ASC CXX)

set(CMAKE_CXX_STANDARD 14)

if(DEFINED NPU_ARCH)
    set(SOC_ARCH ${NPU_ARCH})
else()
    set(SOC_ARCH "dav-2201")
endif()

add_executable(quant_matmul_relu_quant_custom main.asc)
add_executable(bench_pure_cube_2d bench.asc)

target_link_libraries(quant_matmul_relu_quant_custom PRIVATE
    tiling_api
    register
    platform
    unified_dlog
    dl
    m
    graph_base
)

target_include_directories(quant_matmul_relu_quant_custom PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_include_directories(bench_pure_cube_2d PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
)

target_compile_options(quant_matmul_relu_quant_custom PRIVATE
    $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=${SOC_ARCH}>
)

target_compile_options(bench_pure_cube_2d PRIVATE
    $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=${SOC_ARCH}>
)
target_compile_definitions(bench_pure_cube_2d PRIVATE
    BENCH_KERNEL="kernel.asc"
)
target_link_libraries(bench_pure_cube_2d PRIVATE
    tiling_api
    register
    platform
    unified_dlog
    dl
    m
    graph_base
)
