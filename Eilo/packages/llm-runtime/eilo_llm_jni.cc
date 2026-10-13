#include "eilo_llm.h"
#include "ggml-backend.h"
#include <jni.h>
#include <array>
#include <atomic>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace {
void wipe(void *p, size_t n) {
  auto *bytes = static_cast<volatile unsigned char *>(p);
  while (n--) *bytes++ = 0;
}
template <size_t N> struct Scratch {
  std::array<char, N> bytes{};
  ~Scratch() { wipe(bytes.data(), N); }
};
std::atomic<int> live{0};
struct Entry {
  using Core = std::unique_ptr<EiloLlm, decltype(&eilo_llm_destroy)>;
  Core core;
  std::mutex worker;
  explicit Entry(Core &&p) : core(std::move(p)) { ++live; }
  ~Entry() { core.reset(); --live; }
};
std::mutex registry;
std::unordered_map<jlong, std::shared_ptr<Entry>> handles;
jlong next_id = 1;
std::shared_ptr<Entry> find(jlong id) {
  std::lock_guard<std::mutex> lock(registry);
  auto it = handles.find(id);
  return it == handles.end() ? nullptr : it->second;
}
}

#ifdef EILO_LLM_EVALUATION
// Test-only observation proves that the destroy race overlaps an actual native
// worker call. Never emitted when compiling an ordinary runtime library.
extern "C" JNIEXPORT jboolean JNICALL Java_com_eilo_foundation_LlmEvaluationProbe_workerActive(JNIEnv *, jobject, jlong id) {
  auto entry = find(id); if (!entry) return JNI_FALSE;
  std::unique_lock<std::mutex> lock(entry->worker, std::try_to_lock);
  return lock.owns_lock() ? JNI_FALSE : JNI_TRUE;
}
#endif

extern "C" JNIEXPORT jboolean JNICALL Java_com_eilo_foundation_NativeLlmJni_runtimeCompatible(JNIEnv *, jobject) {
  return JNI_TRUE; // This binding ABI probe is not model or publication trust.
}
extern "C" JNIEXPORT jlong JNICALL Java_com_eilo_foundation_NativeLlmJni_create(JNIEnv *, jobject) {
  std::lock_guard<std::mutex> lock(registry);
  try {
    if (live.load() >= 4 || next_id <= 0 || next_id == INT64_MAX) return 0;
    std::unique_ptr<EiloLlm, decltype(&eilo_llm_destroy)> core(eilo_llm_create(), eilo_llm_destroy);
    if (!core) return 0;
    auto entry = std::make_shared<Entry>(std::move(core));
    jlong id = next_id++;
    handles.emplace(id, std::move(entry));
    return id;
  } catch (...) { return 0; }
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeLlmJni_load(JNIEnv *, jobject, jlong id, jint fd, jint threads) {
  auto entry = find(id); if (!entry) return EILO_LLM_INVALID;
  std::unique_lock<std::mutex> lock(entry->worker, std::try_to_lock);
  if (!lock.owns_lock()) return EILO_LLM_INVALID;
  return eilo_llm_load(entry->core.get(), fd, threads);
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeLlmJni_countTokens(JNIEnv *env, jobject, jlong id,
    jbyteArray text, jint count) {
  auto entry = find(id);
  if (!entry || !text || count < 1 || count > 16384 || count > env->GetArrayLength(text)) return EILO_LLM_INVALID;
  std::unique_lock<std::mutex> lock(entry->worker, std::try_to_lock);
  if (!lock.owns_lock()) return EILO_LLM_INVALID;
  Scratch<16384> scratch;
  env->GetByteArrayRegion(text, 0, count, reinterpret_cast<jbyte *>(scratch.bytes.data()));
  if (env->ExceptionCheck()) return EILO_LLM_UNAVAILABLE;
  return eilo_llm_count_tokens(entry->core.get(), scratch.bytes.data(), count);
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeLlmJni_begin(JNIEnv *env, jobject, jlong id,
    jbyteArray prompt, jint count, jint limit) {
  auto entry = find(id);
  if (!entry || !prompt || count < 1 || count > 16384 || count > env->GetArrayLength(prompt)) return EILO_LLM_INVALID;
  std::unique_lock<std::mutex> lock(entry->worker, std::try_to_lock);
  if (!lock.owns_lock()) return EILO_LLM_INVALID;
  Scratch<16384> scratch;
  env->GetByteArrayRegion(prompt, 0, count, reinterpret_cast<jbyte *>(scratch.bytes.data()));
  if (env->ExceptionCheck()) return EILO_LLM_UNAVAILABLE;
  return eilo_llm_begin(entry->core.get(), scratch.bytes.data(), count, limit);
}
extern "C" JNIEXPORT jint JNICALL Java_com_eilo_foundation_NativeLlmJni_next(JNIEnv *env, jobject, jlong id,
    jbyteArray output, jintArray count) {
  if (!count || env->GetArrayLength(count) != 1) return EILO_LLM_INVALID;
  jint bytes = 0; env->SetIntArrayRegion(count, 0, 1, &bytes);
  if (!output || env->GetArrayLength(output) != 1024 || env->ExceptionCheck()) return EILO_LLM_INVALID;
  Scratch<1024> scratch;
  env->SetByteArrayRegion(output, 0, 1024, reinterpret_cast<const jbyte *>(scratch.bytes.data()));
  if (env->ExceptionCheck()) return EILO_LLM_UNAVAILABLE;
  auto entry = find(id); if (!entry) return EILO_LLM_INVALID;
  std::unique_lock<std::mutex> lock(entry->worker, std::try_to_lock);
  if (!lock.owns_lock()) return EILO_LLM_INVALID;
  int32_t n = 0;
  int result = eilo_llm_next(entry->core.get(), scratch.bytes.data(), 1024, &n);
  if (result != EILO_LLM_TOKEN) return result;
  if (n < 1 || n > 1024) return EILO_LLM_UNAVAILABLE;
  env->SetByteArrayRegion(output, 0, n, reinterpret_cast<const jbyte *>(scratch.bytes.data()));
  if (env->ExceptionCheck()) return EILO_LLM_UNAVAILABLE;
  bytes = n; env->SetIntArrayRegion(count, 0, 1, &bytes);
  return env->ExceptionCheck() ? EILO_LLM_UNAVAILABLE : EILO_LLM_TOKEN;
}
extern "C" JNIEXPORT void JNICALL Java_com_eilo_foundation_NativeLlmJni_cancel(JNIEnv *, jobject, jlong id) {
  auto entry = find(id); if (entry) eilo_llm_cancel(entry->core.get());
}
extern "C" JNIEXPORT void JNICALL Java_com_eilo_foundation_NativeLlmJni_destroy(JNIEnv *, jobject, jlong id) {
  std::shared_ptr<Entry> old;
  {
    std::lock_guard<std::mutex> lock(registry);
    auto it = handles.find(id); if (it == handles.end()) return;
    old = std::move(it->second); handles.erase(it);
  }
  // The active worker retains a shared lifetime until it returns. No global gate
  // blocks cancellation behind model load/decode; IDs are never reused as pointers.
  eilo_llm_cancel(old->core.get());
}
