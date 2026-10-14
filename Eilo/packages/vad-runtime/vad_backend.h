#ifndef EILO_VAD_BACKEND_H
#define EILO_VAD_BACKEND_H
#include <memory>
struct VadBackend {
  virtual ~VadBackend() = default;
  virtual bool infer(const float *input576, const float *state256,
                     float *probability, float *next256) = 0;
};
std::unique_ptr<VadBackend> open_vad_backend(const char *model);
#endif
