#ifndef EILO_ASR_H
#define EILO_ASR_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct EiloAsr EiloAsr;
/* One worker, one independently verified Small Streaming English model, one <=30s turn.
 * Linking does not grant manifest trust or production readiness. No downloader/microphone. */
EiloAsr *eilo_asr_create(const char *model_directory);
int32_t eilo_asr_accept(EiloAsr *, const float *, int32_t count);
/* Copies at most4096 UTF-8 bytes plus NUL. 0=success, -1=closed/invalid/unavailable.
 * finish drains the vendor stream once. Caller clears output and destroys on cancellation. */
int32_t eilo_asr_text(EiloAsr *, int32_t finish, char *output, int32_t capacity);
void eilo_asr_destroy(EiloAsr *);
#ifdef __cplusplus
}
#endif
#endif
