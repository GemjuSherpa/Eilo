// Appended to the existing scripted backend prefix by check_phase_contract.py.
#include "eilo_trial_metrics.h"
#include <cmath>
#include <thread>

int main() {

  double values[7];
  auto unavailable = [&] {
    for (double &v : values) v = -1;
    CHECK(eilo_trial_phase_metrics(values, 7) == 0);
    for (double v : values) CHECK(v == 0);
  };
  reset();
  FILE *file = std::tmpfile(); CHECK(file);
  CHECK(ftruncate(fileno(file), 1282439424) == 0);
  loaded(fileno(file)); unavailable();
  CHECK(eilo_llm_begin(current, "fixture", 7, 2) == 0);
  CHECK(next() == EILO_LLM_TOKEN); unavailable();
  CHECK(next() == EILO_LLM_TOKEN); unavailable();
  CHECK(next() == EILO_LLM_DONE);
  CHECK(eilo_trial_phase_metrics(values, 7) == 1);
  for (double v : values) CHECK(std::isfinite(v) && v >= 0);
  CHECK(values[5] >= values[1] + values[2] + values[3] + values[4]);
  CHECK(values[6] >= values[5]);
  finish(); CHECK(eilo_trial_phase_metrics(values, 7) == 1);
  std::thread isolated([&] { double own[7]; CHECK(eilo_trial_phase_metrics(own, 7) == 0); }); isolated.join();
  values[0] = 123; CHECK(eilo_trial_phase_metrics(values, 6) == 0 && values[0] == 123);
  CHECK(eilo_trial_phase_metrics(nullptr, 7) == 0);
  reset(); begun(fileno(file)); unavailable();
  eilo_llm_cancel(current); CHECK(next() == EILO_LLM_CANCELLED); unavailable(); finish();
  reset(); fail_load = true; CHECK(eilo_llm_load(current, fileno(file), 2) == EILO_LLM_UNAVAILABLE); unavailable(); finish();
  std::fclose(file);
  std::puts("Lab phase metrics: completion, cleanup, revocation, capacity, clock order and thread isolation PASS");
  return 0;
}
