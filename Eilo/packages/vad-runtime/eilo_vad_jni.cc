#include "eilo_vad.h"
#include <jni.h>
#include <array>
#include <cstring>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace {
using Owned=std::unique_ptr<EiloVad,decltype(&eilo_vad_destroy)>;
std::mutex gate;
std::unordered_map<jlong,Owned> handles;
jlong next_id=1;
void erase(float *p,size_t count){volatile float *v=p;while(count--)*v++=0;}
}
extern "C" JNIEXPORT jlong JNICALL Java_com_eilo_foundation_NativeVadJni_createNative(JNIEnv *env,jobject,jbyteArray path){
  std::lock_guard<std::mutex> lock(gate);
  try {
    if(!path || next_id<=0 || next_id==INT64_MAX)return 0;
    const int size=env->GetArrayLength(path);if(size<1 || size>4096)return 0;
    std::array<char,4097> model{};
    env->GetByteArrayRegion(path,0,size,reinterpret_cast<jbyte*>(model.data()));
    if(env->ExceptionCheck() || std::memchr(model.data(),0,size))return 0;
    Owned stream(eilo_vad_create(model.data()),eilo_vad_destroy);
    volatile char *bytes=model.data();for(size_t i=0;i<model.size();++i)bytes[i]=0;
    if(!stream)return 0;
    const jlong id=next_id++;handles.emplace(id,std::move(stream));return id;
  }catch(...){return 0;}
}
extern "C" JNIEXPORT jdoubleArray JNICALL Java_com_eilo_foundation_NativeVadJni_processNative(JNIEnv *env,jobject,jlong id,jfloatArray pcm,jint count,jboolean final){
  std::lock_guard<std::mutex> lock(gate);
  auto found=handles.find(id);if(found==handles.end())return nullptr;
  auto fail=[&]()->jdoubleArray{handles.erase(found);return nullptr;};
  try {
    if(!pcm || count<1 || count>512 || count>env->GetArrayLength(pcm))return fail();
    std::array<float,512> scratch{};
    struct Clear{std::array<float,512>&v;~Clear(){erase(v.data(),v.size());}} clear{scratch};
    env->GetFloatArrayRegion(pcm,0,count,scratch.data());
    EiloVadFrame frame{};
    if(env->ExceptionCheck() || eilo_vad_process(found->second.get(),scratch.data(),count,final?1:0,&frame)!=0)return fail();
    const std::array<jdouble,4> values={frame.probability,static_cast<double>(frame.start_sample),
                                     static_cast<double>(frame.samples),static_cast<double>(frame.final_frame)};
    jdoubleArray result=env->NewDoubleArray(4);
    if(!result)return fail();
    env->SetDoubleArrayRegion(result,0,4,values.data());
    if(env->ExceptionCheck())return fail();
    return result;
  }catch(...){return fail();}
}
extern "C" JNIEXPORT void JNICALL Java_com_eilo_foundation_NativeVadJni_destroyNative(JNIEnv *,jobject,jlong id){
  std::lock_guard<std::mutex> lock(gate);handles.erase(id);
}
