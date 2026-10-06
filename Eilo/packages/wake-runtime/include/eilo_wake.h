#ifndef EILO_WAKE_H
#define EILO_WAKE_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
// Serialized native-worker API. Inputs must come from independently verified local assets.
// This layer does not provide manifest trust or make production model readiness available.
typedef struct EiloWake EiloWake;
EiloWake *eilo_wake_create(const char *encoder, const char *decoder, const char *joiner,
                         const char *tokens, float threshold, float boost);
// -1: unavailable/invalid; 0: no wake; 1: configured HEY_EILO wake only.
// Borrowed mono Float samples are consumed synchronously, never retained by this wrapper.
int32_t eilo_wake_process(EiloWake *wake, const float *samples, int32_t count, int32_t rate);
void eilo_wake_destroy(EiloWake *wake);
#ifdef __cplusplus
}
#endif
#endif
