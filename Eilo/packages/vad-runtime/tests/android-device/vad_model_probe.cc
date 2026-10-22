// Invocation-only diagnostic: fixed classifications, never raw model/error/path text.
#include "../../vad_backend.h"
#include "onnxruntime_cxx_api.h"
#include <jni.h>
#include <algorithm>
#include <cctype>
#include <string>
#include <vector>
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_ArtVadProbe_modelStatus(JNIEnv *env,jclass,jbyteArray bytes) {
  if(!bytes)return -1;
  const auto size=env->GetArrayLength(bytes);
  if(size<=0 || size>4096)return -1;
  std::vector<char> path(static_cast<size_t>(size)+1,0);
  env->GetByteArrayRegion(bytes,0,size,reinterpret_cast<jbyte*>(path.data()));
  if(env->ExceptionCheck() || std::find(path.begin(),path.end()-1,'\0')!=path.end()-1)return -1;
  int result=0;
  try{auto backend=open_vad_backend(path.data());if(!backend)result=-1;}
  catch(const Ort::Exception &error){
    result=static_cast<int>(error.GetOrtErrorCode());
    std::string detail=error.what();
    std::transform(detail.begin(),detail.end(),detail.begin(),[](unsigned char c){return static_cast<char>(std::tolower(c));});
    if(detail.find("onnx format")!=std::string::npos && detail.find("not supported")!=std::string::npos)result=1001;
    else if(detail.find("no op registered")!=std::string::npos || detail.find("could not find an implementation")!=std::string::npos)result=1002;
  }catch(...){result=-1;}
  std::fill(path.begin(),path.end(),0);return result;
}
