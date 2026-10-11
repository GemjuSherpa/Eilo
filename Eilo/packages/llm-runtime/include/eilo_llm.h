#ifndef EILO_LLM_H
#define EILO_LLM_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
typedef struct EiloLlm EiloLlm;
enum EiloLlmResult {
  EILO_LLM_DONE = 0, EILO_LLM_TOKEN = 1,
  EILO_LLM_INVALID = -1, EILO_LLM_CANCELLED = -2, EILO_LLM_UNAVAILABLE = -3
};
/* One worker owns all calls except cancel. Destroy only after the worker joins.
 * One handle is one generation; cancellation is permanent, including before load.
 * Linking this core does not establish signed-pack trust or app readiness. */
EiloLlm *eilo_llm_create(void);
/* Caller verifies SHA-256 on this open, immutable, exclusively borrowed descriptor.
 * The adapter duplicates it, loads from that descriptor (no path reopen), and checks
 * regular-file size, Qwen3 architecture and Q4_K_M metadata. Threads: 1..8. */
int32_t eilo_llm_load(EiloLlm *, int32_t verified_model_fd, int32_t threads);
/* Preformatted native prompt only; no chat-template/policy/speech authorization.
 * <=16384 bytes, <=4096 total prompt+output tokens, output limit 1..256. */
int32_t eilo_llm_begin(EiloLlm *, const char *prompt, int32_t bytes, int32_t output_limit);
/* TOKEN copies a raw token byte piece, which may split UTF-8; never speech-ready.
 * Caller provides exactly 1024 bytes, clears them after use and rechecks the current
 * controller/privacy/model lease before any downstream release. All other results
 * return zero bytes. No final token is replayed after completion/cancellation. */
int32_t eilo_llm_next(EiloLlm *, char *output, int32_t capacity, int32_t *bytes);
void eilo_llm_cancel(EiloLlm *);
void eilo_llm_destroy(EiloLlm *);
#ifdef __cplusplus
}
#endif
#endif
