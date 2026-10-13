#include "ggml-backend.h"
#include <jni.h>
#include <cerrno>
#include <initializer_list>
#include <utility>
#include <sys/socket.h>
#include <unistd.h>

// Explicit evaluation-only probes; not part of normal app/library packaging.
extern "C" JNIEXPORT jboolean JNICALL Java_com_eilo_foundation_LlmEvaluationProbe_cpuOnly(JNIEnv *, jobject) {
  if (ggml_backend_dev_count() == 0) return JNI_FALSE;
  for (size_t i = 0; i < ggml_backend_dev_count(); ++i)
    if (ggml_backend_dev_type(ggml_backend_dev_get(i)) != GGML_BACKEND_DEVICE_TYPE_CPU) return JNI_FALSE;
  return JNI_TRUE;
}
extern "C" JNIEXPORT jboolean JNICALL Java_com_eilo_foundation_LlmEvaluationProbe_networkDenied(JNIEnv *, jobject) {
  for (auto pair : {std::pair<int, int>{AF_INET, SOCK_STREAM}, {AF_INET6, SOCK_STREAM}, {AF_INET, SOCK_DGRAM}}) {
    errno = 0;
    int fd = socket(pair.first, pair.second, 0);
    int error = errno;
    if (fd >= 0) { close(fd); return JNI_FALSE; }
    if (error != EACCES && error != EPERM) return JNI_FALSE;
  }
  return JNI_TRUE;
}
