#include "eilo_wake.h"
#include <jni.h>
#include <array>
#include <cmath>
#include <limits>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace {
// IDs never expose/reuse pointers. JNI calls serialize lookup, borrow and destruction.
struct Session {
  EiloWake *wake;
  std::array<float,19200> scratch{};
  explicit Session(EiloWake *value):wake(value) {}
  void erase() { volatile float *p=scratch.data();for(size_t i=0;i<scratch.size();++i)p[i]=0; }
  ~Session() { erase();eilo_wake_destroy(wake); }
};
std::mutex mutex;
std::unordered_map<jlong,std::unique_ptr<Session>> sessions;
jlong next_id=1;
struct Path {
  JNIEnv *env; jstring value; const char *text=nullptr;
  Path(JNIEnv *e,jstring s):env(e),value(s) {
    if(s && env->GetStringUTFLength(s)<=4096)text=env->GetStringUTFChars(s,nullptr);
  }
  bool valid() const { return text && text[0]=='/'; }
  ~Path() { if(text)env->ReleaseStringUTFChars(value,text); }
};
}
extern "C" JNIEXPORT jlong JNICALL Java_com_eilo_foundation_NativeWakeJNI_createNative(
    JNIEnv *env,jobject,jstring encoder,jstring decoder,jstring joiner,jstring tokens,jfloat threshold,jfloat boost) {
  std::lock_guard<std::mutex> guard(mutex);
  try {
    // Do not make further JNI calls when a failed string borrow leaves an exception pending.
    Path e(env,encoder);if(env->ExceptionCheck() || !e.valid())return 0;
    Path d(env,decoder);if(env->ExceptionCheck() || !d.valid())return 0;
    Path j(env,joiner);if(env->ExceptionCheck() || !j.valid())return 0;
    Path t(env,tokens);if(env->ExceptionCheck() || !t.valid())return 0;
    if(next_id==std::numeric_limits<jlong>::max())return 0;
    std::unique_ptr<EiloWake,decltype(&eilo_wake_destroy)> candidate(
        eilo_wake_create(e.text,d.text,j.text,t.text,threshold,boost),eilo_wake_destroy);
    if(!candidate)return 0;
    auto session=std::make_unique<Session>(candidate.get());candidate.release();
    const jlong id=next_id++;
    sessions.emplace(id,std::move(session));return id;
  } catch (...) { return 0; }
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeWakeJNI_processNative(
    JNIEnv *env,jobject,jlong id,jfloatArray samples,jint count,jint rate) {
  std::lock_guard<std::mutex> guard(mutex);
  auto found=sessions.find(id);
  if(found==sessions.end())return -1;
  Session &session=*found->second;
  try {
    if(!samples || rate<8000 || rate>192000 || count<=0 || count>rate/10 ||
       count>env->GetArrayLength(samples)) { sessions.erase(found);return -1; }
    env->GetFloatArrayRegion(samples,0,count,session.scratch.data());
    if(env->ExceptionCheck()) { sessions.erase(found);return -1; }
    const int result=eilo_wake_process(session.wake,session.scratch.data(),count,rate);
    session.erase();
    if(result!=0 && result!=1) { sessions.erase(found);return -1; }
    return result;
  } catch (...) { sessions.erase(found);return -1; }
}
extern "C" JNIEXPORT void JNICALL Java_com_eilo_foundation_NativeWakeJNI_destroyNative(JNIEnv*,jobject,jlong id) {
  std::lock_guard<std::mutex> guard(mutex);sessions.erase(id);
}
