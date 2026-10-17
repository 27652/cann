cmake_minimum_required(VERSION 3.16)
find_package(ASC REQUIRED)
project(fp32_activation_cache LANGUAGES ASC CXX)
set(CMAKE_CXX_STANDARD 14)
add_executable(fp32_activation_cache main.asc)
target_compile_options(fp32_activation_cache PRIVATE
    $<$<COMPILE_LANGUAGE:ASC>:--npu-arch=dav-2201>)
target_link_libraries(fp32_activation_cache PRIVATE
    tiling_api register platform unified_dlog dl m graph_base)
set(SIM_LIB "$ENV{ASCEND_HOME_PATH}/x86_64-linux/simulator/dav_2201/lib")
if(EXISTS "${SIM_LIB}/libascendcl.so")
    target_link_libraries(fp32_activation_cache PRIVATE "${SIM_LIB}/libascendcl.so")
    set_target_properties(fp32_activation_cache PROPERTIES BUILD_RPATH "${SIM_LIB}")
endif()
