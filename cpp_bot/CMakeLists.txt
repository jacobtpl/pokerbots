cmake_minimum_required(VERSION 3.2)

# Replace "cpp-pokerbot" with your bot's name
project(cpp-bot)

set(CMAKE_CXX_STANDARD 17)

add_subdirectory(libs)
add_subdirectory(OMPEval)

file(GLOB_RECURSE BOT_SRC ${PROJECT_SOURCE_DIR}/src/*.cpp)

add_executable(pokerbot ${BOT_SRC})
target_include_directories(pokerbot PUBLIC ${PROJECT_SOURCE_DIR}/include)
target_link_libraries(pokerbot skeleton)
target_link_libraries(pokerbot omp)
