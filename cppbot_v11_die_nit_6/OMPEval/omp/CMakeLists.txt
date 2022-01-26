project(cpp-skeleton)

file(GLOB_RECURSE SKELETON_SRC ${PROJECT_SOURCE_DIR}/src/*.cpp)
file(GLOB_RECURSE SKELETON_HEADERS ${PROJECT_SOURCE_DIR}/src/*.h)

add_library(skeleton STATIC ${SKELETON_SRC})
target_include_directories(skeleton PUBLIC ${PROJECT_SOURCE_DIR}/include)

set(Boost_USE_STATIC_LIBS ON)
set(Boost_USE_MULTITHREAD OFF)


set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)
target_link_libraries(omp PUBLIC Threads::Threads)
