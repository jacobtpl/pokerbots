project(omp-eval)

file(GLOB_RECURSE OMP_SRC ${PROJECT_SOURCE_DIR}/omp/*.cpp)
file(GLOB_RECURSE LIBDIVIDE_HEADERS ${PROJECT_SOURCE_DIR}/libdivide/*.h)
file(GLOB_RECURSE OMP_HEADERS ${PROJECT_SOURCE_DIR}/omp/*.h)

add_library(omp STATIC ${OMP_SRC})
target_include_directories(omp PUBLIC ${PROJECT_SOURCE_DIR})
