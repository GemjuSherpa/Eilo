cmake_minimum_required(VERSION 3.22)
project(corpus_score_probe CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CORE "${SOURCE_ROOT}/core")
add_executable(corpus-score-probe main.cpp ${OVERLAY}/moonshine-streaming-model.cpp
 ${CORE}/context-biaser.cpp ${CORE}/bin-tokenizer/bin-tokenizer.cpp
 ${CORE}/moonshine-utils/string-utils.cpp ${CORE}/moonshine-utils/debug-utils.cpp
 ${CORE}/moonshine-utils/file-utils.cpp ${CORE}/moonshine-utils/file-information.cpp
 ${CORE}/ort-utils/ort-utils.cpp ${CORE}/ort-utils/ort-utils-ep.cpp
 ${CORE}/ort-utils/moonshine-ort-allocator.cpp ${CORE}/ort-utils/moonshine-tensor.cpp
 ${CORE}/ort-utils/moonshine-tensor-view.cpp)
target_include_directories(corpus-score-probe PRIVATE ${OVERLAY} ${CMAKE_CURRENT_SOURCE_DIR} ${SCORE_HEADERS} ${CORE} ${CORE}/bin-tokenizer ${CORE}/moonshine-utils ${CORE}/ort-utils ${CORE}/third-party/onnxruntime/include ${CORE}/third-party/nlohmann)
target_link_libraries(corpus-score-probe PRIVATE "${ORT_LIBRARY}" android log)
