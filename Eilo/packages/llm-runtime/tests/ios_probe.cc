#include "ggml-backend.h"
#include "ios_probe.h"
extern "C" int32_t eilo_llm_eval_cpu_only(void) {
  if (ggml_backend_dev_count() == 0) return 0;
  for (size_t i = 0; i < ggml_backend_dev_count(); ++i)
    if (ggml_backend_dev_type(ggml_backend_dev_get(i)) != GGML_BACKEND_DEVICE_TYPE_CPU) return 0;
  return 1;
}
