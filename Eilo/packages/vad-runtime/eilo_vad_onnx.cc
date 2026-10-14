#include "vad_backend.h"
#include "onnxruntime_cxx_api.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace {
class OnnxVad final:public VadBackend {
  Ort::Env env{ORT_LOGGING_LEVEL_FATAL,"eilo-vad"};
  Ort::SessionOptions options;
  Ort::Session session{nullptr};
  Ort::MemoryInfo memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
public:
  explicit OnnxVad(const char *model) {
    options.SetIntraOpNumThreads(1);options.SetInterOpNumThreads(1);
    session=Ort::Session(env,model,options);
    Ort::AllocatorWithDefaultOptions allocator;
    const std::array<std::string,3> inputs={"input","state","sr"};
    const std::array<std::string,2> outputs={"output","stateN"};
    if(session.GetInputCount()!=3 || session.GetOutputCount()!=2)throw std::runtime_error("VAD schema");
    for(size_t i=0;i<inputs.size();++i)if(inputs[i]!=session.GetInputNameAllocated(i,allocator).get())throw std::runtime_error("VAD input");
    for(size_t i=0;i<outputs.size();++i)if(outputs[i]!=session.GetOutputNameAllocated(i,allocator).get())throw std::runtime_error("VAD output");
  }
  bool infer(const float *input,const float *state,float *probability,float *next) override {
    const std::array<int64_t,2> audio_shape={1,576};
    const std::array<int64_t,3> state_shape={2,1,128};
    int64_t rate=16000;
    std::array<Ort::Value,3> tensors={
      Ort::Value::CreateTensor<float>(memory,const_cast<float*>(input),576,audio_shape.data(),2),
      Ort::Value::CreateTensor<float>(memory,const_cast<float*>(state),256,state_shape.data(),3),
      Ort::Value::CreateTensor<int64_t>(memory,&rate,1,nullptr,0)};
    const char *names[]={"input","state","sr"};const char *outputs[]={"output","stateN"};
    auto values=session.Run(Ort::RunOptions{nullptr},names,tensors.data(),3,outputs,2);
    if(values.size()!=2 || !values[0].IsTensor() || !values[1].IsTensor())return false;
    auto p=values[0].GetTensorTypeAndShapeInfo(),s=values[1].GetTensorTypeAndShapeInfo();
    if(p.GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
       s.GetElementType()!=ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT ||
       p.GetShape()!=std::vector<int64_t>({1,1}) || s.GetShape()!=std::vector<int64_t>({2,1,128}))return false;
    *probability=values[0].GetTensorData<float>()[0];
    std::copy_n(values[1].GetTensorData<float>(),256,next);
    return true;
  }
};
}
std::unique_ptr<VadBackend> open_vad_backend(const char *model){return std::make_unique<OnnxVad>(model);}
