"""Opt-in lab telemetry derived from the exact reviewed adapter, without lifecycle changes."""
import hashlib
from model_wrapper import wrapper

KEYS = ('model_load_ms', 'tokenize_ms', 'context_setup_ms', 'prefill_ms',
        'first_sample_ms', 'begin_to_first_token_ms', 'begin_to_first_piece_ms')


def phase_wrapper(source, pin):
    compiled, evidence = wrapper(source, pin)
    def change(old, new):
        nonlocal compiled
        old, new = old.encode(), new.encode()
        if compiled.count(old) != 1:
            raise ValueError('Unreviewed telemetry insertion boundary')
        compiled = compiled.replace(old, new)
    change('#include <array>', '#include <array>\n#include <chrono>\n#include "eilo_trial_metrics.h"')
    change('namespace {', '''namespace {
using TrialClock = std::chrono::steady_clock;
static_assert(TrialClock::is_steady, "monotonic clock required");
struct TrialMetrics {
  double values[7]{};
  TrialClock::time_point begin{};
  bool first = false, complete = false;
};
thread_local TrialMetrics trial_metrics;
double trial_ms(TrialClock::time_point start) {
  return std::chrono::duration<double, std::milli>(TrialClock::now() - start).count();
}''')
    change('clear(); state = reason == EILO_LLM_DONE ? State::done : State::failed;', '''trial_metrics.complete = reason == EILO_LLM_DONE && trial_metrics.first;
    clear(); state = reason == EILO_LLM_DONE ? State::done : State::failed;''')
    change('if (!h) return EILO_LLM_INVALID;\n  if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);\n  if (h->state != EiloLlm::State::created)', '''trial_metrics = TrialMetrics{};
  if (!h) return EILO_LLM_INVALID;
  if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
  if (h->state != EiloLlm::State::created)''')
    change('h->model = llama_model_load_from_file_ptr(file, params);', '''auto trial_load_start = TrialClock::now();
    h->model = llama_model_load_from_file_ptr(file, params);
    trial_metrics.values[0] = trial_ms(trial_load_start);''')
    change('Tokens tokens;\n    auto *vocab', '''trial_metrics.begin = TrialClock::now();
    auto trial_tokenize_start = TrialClock::now();
    Tokens tokens;
    auto *vocab''')
    change('if (count < 1 || count > kContext - limit)', '''trial_metrics.values[1] = trial_ms(trial_tokenize_start);
    if (count < 1 || count > kContext - limit)''')
    change('auto params = llama_context_default_params();', '''auto trial_context_start = TrialClock::now();
    auto params = llama_context_default_params();''')
    change('for (int offset = 0; offset < count; offset += kBatch)', '''trial_metrics.values[2] = trial_ms(trial_context_start);
    auto trial_prefill_start = TrialClock::now();
    for (int offset = 0; offset < count; offset += kBatch)''')
    change('h->limit = limit; h->state', '''trial_metrics.values[3] = trial_ms(trial_prefill_start);
    h->limit = limit; h->state''')
    change('llama_token token = llama_sampler_sample(h->sampler, h->context, -1);', '''auto trial_sample_start = TrialClock::now();
    llama_token token = llama_sampler_sample(h->sampler, h->context, -1);
    if (h->generated == 0) {
      trial_metrics.values[4] = trial_ms(trial_sample_start);
      trial_metrics.values[5] = trial_ms(trial_metrics.begin);
    }''')
    change('std::memcpy(out, piece.data.data(), size);', '''if (h->generated == 0) {
      trial_metrics.values[6] = trial_ms(trial_metrics.begin);
      trial_metrics.first = true;
    }
    std::memcpy(out, piece.data.data(), size);''')
    compiled += b'''
// Worker-thread aggregate only. No handle, prompt or token content is exposed.
extern "C" int32_t eilo_trial_phase_metrics(double *out, int32_t count) {
  if (!out || count != 7) return 0;
  for (int i = 0; i < count; ++i) out[i] = 0;
  if (!trial_metrics.complete) return 0;
  for (int i = 0; i < count; ++i) out[i] = trial_metrics.values[i];
  return 1;
}
'''
    evidence.update(scope='LAB_ONLY_NATIVE_PHASE_TELEMETRY',
                    size_specialized_source_sha256=evidence['compiled_source_sha256'],
                    compiled_source_sha256=hashlib.sha256(compiled).hexdigest(),
                    timing_clock='std::chrono::steady_clock', timing_fields=list(KEYS),
                    change='Exact size specialization plus numeric thread-local monotonic phase timing; original checks and cleanup retained')
    return compiled, evidence
