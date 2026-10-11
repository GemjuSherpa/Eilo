#include "eilo_asr.h"
#include <jni.h>
#include <array>
#include <cstring>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace {
using Owned=std::unique_ptr<EiloAsr,decltype(&eilo_asr_destroy)>;
std::mutex gate;
std::unordered_map<jlong,Owned> handles;
jlong next_id=1;
}
extern "C" JNIEXPORT jlong JNICALL Java_com_eilo_foundation_NativeAsrJni_create(JNIEnv *env,jobject,jbyteArray path){
  std::lock_guard<std::mutex> lock(gate);
  try {
    if(!path || next_id<=0 || next_id==INT64_MAX)return 0;
    int n=env->GetArrayLength(path);if(n<1 || n>4096)return 0;
    std::array<char,4097> directory{};env->GetByteArrayRegion(path,0,n,reinterpret_cast<jbyte *>(directory.data()));
    if(env->ExceptionCheck() || std::memchr(directory.data(),0,n))return 0;
    Owned a(eilo_asr_create(directory.data()),eilo_asr_destroy);directory.fill(0);
    if(!a)return 0;
    jlong id=next_id++;handles.emplace(id,std::move(a));return id;
  }catch(...){return 0;}
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeAsrJni_accept(JNIEnv *env,jobject,jlong id,jfloatArray input,jint count){
  std::lock_guard<std::mutex> lock(gate);
  auto found=handles.find(id);
  if(found==handles.end() || !input || count<1 || count>1600 || count>env->GetArrayLength(input))return -1;
  std::array<float,1600> scratch{};
  env->GetFloatArrayRegion(input,0,count,scratch.data());
  int result=env->ExceptionCheck()?-1:eilo_asr_accept(found->second.get(),scratch.data(),count);
  scratch.fill(0);return result;
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_com_eilo_foundation_NativeAsrJni_read(JNIEnv *env,jobject,jlong id,jboolean finish){
  std::lock_guard<std::mutex> lock(gate);
  auto found=handles.find(id);if(found==handles.end())return nullptr;
  std::array<char,4097> text{};
  if(eilo_asr_text(found->second.get(),finish?1:0,text.data(),4097)!=0)return nullptr;
  int n=static_cast<int>(std::strlen(text.data()));jbyteArray result=env->NewByteArray(n);
  if(result)env->SetByteArrayRegion(result,0,n,reinterpret_cast<const jbyte *>(text.data()));
  text.fill(0);return result;
}
extern "C" JNIEXPORT void JNICALL Java_com_eilo_foundation_NativeAsrJni_destroy(JNIEnv *,jobject,jlong id){
  std::lock_guard<std::mutex> lock(gate);handles.erase(id);
}
