// Offline conversion using the verified cached Moonshine host runtime and matching headers.
#include "onnxruntime_cxx_api.h"
#include <cstdio>
#include <filesystem>
#include <string>
int main(int argc,char **argv){
  if(argc!=3 || std::filesystem::exists(argv[2]))return 2;
  if(std::string(OrtGetApiBase()->GetVersionString())!="1.23.0")return 3;
  std::puts("HOST_ORT_1.23.0");
  try{
    Ort::Env env(ORT_LOGGING_LEVEL_FATAL,"eilo-local-conversion");Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1);options.SetInterOpNumThreads(1);
    options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);
    options.SetOptimizedModelFilePath(argv[2]);options.AddConfigEntry("session.save_model_format","ORT");
    Ort::Session session(env,argv[1],options);
    if(session.GetInputCount()!=3 || session.GetOutputCount()!=2)return 4;
    std::puts("ORT_CONVERSION_PASS");return 0;
  }catch(const Ort::Exception &error){std::printf("ORT_ERROR_%d\n",static_cast<int>(error.GetOrtErrorCode()));return 1;}
}
