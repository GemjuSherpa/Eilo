cmake_minimum_required(VERSION 3.22)
project(ios_sdk_score_probe CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CORE "${SOURCE_ROOT}/core")
add_executable(sdk-score-probe ${CMAKE_CURRENT_LIST_DIR}/../main.cpp ${OVERLAY}/moonshine-streaming-model.cpp
 ${CORE}/context-biaser.cpp ${CORE}/bin-tokenizer/bin-tokenizer.cpp
 ${CORE}/moonshine-utils/string-utils.cpp ${CORE}/moonshine-utils/debug-utils.cpp
 ${CORE}/moonshine-utils/file-utils.cpp ${CORE}/moonshine-utils/file-information.cpp
 ${CORE}/ort-utils/ort-utils.cpp ${CORE}/ort-utils/ort-utils-ep.cpp
 ${CORE}/ort-utils/moonshine-ort-allocator.cpp ${CORE}/ort-utils/moonshine-tensor.cpp
 ${CORE}/ort-utils/moonshine-tensor-view.cpp)
target_include_directories(sdk-score-probe PRIVATE ${OVERLAY} ${CMAKE_CURRENT_LIST_DIR}/.. ${CORE} ${CORE}/bin-tokenizer ${CORE}/moonshine-utils ${CORE}/ort-utils ${CORE}/third-party/onnxruntime/include ${CORE}/third-party/nlohmann)
# Only the already approved static Apple ORT and built-in SDK frameworks.
set_target_properties(sdk-score-probe PROPERTIES MACOSX_BUNDLE FALSE)
target_link_libraries(sdk-score-probe PRIVATE "${ORT_LIBRARY}" "-framework CoreML" "-framework Foundation" "-framework Accelerate")
