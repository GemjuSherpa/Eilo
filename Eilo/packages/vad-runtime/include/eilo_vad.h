#ifndef EILO_VAD_H
#define EILO_VAD_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct EiloVad EiloVad;
typedef struct EiloVadFrame {
  float probability;
  int32_t start_sample;
  int32_t samples;
  int32_t final_frame;
} EiloVadFrame;
/* Caller owns verified local model selection and one-worker stream lifetime.
 * Fixed 16 kHz mono float PCM. No microphone, downloader, readiness or controller access. */
EiloVad *eilo_vad_create(const char *absolute_model);
/* Nonfinal frames are exactly 512 samples; a final frame may contain 1..512.
 * Tail padding is inference-only. Output timestamps/counts exclude padding.
 * Return 0 on success, -1 on failure. Any failure terminally revokes the stream.
 * Probability output covers the native 32 ms window, NOT an invented 20 ms score. */
int32_t eilo_vad_process(EiloVad *, const float *, int32_t count, int32_t final_frame, EiloVadFrame *);
void eilo_vad_destroy(EiloVad *);
#ifdef __cplusplus
}
#endif
#endif
