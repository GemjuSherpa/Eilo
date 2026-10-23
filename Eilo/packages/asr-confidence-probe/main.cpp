#include "moonshine-streaming-model.h"
#include "probability.h"

#include <cstdio>
#include <fstream>
#include <memory>
#include <vector>

int main(int argc, char** argv) {
  try {
    require(argc == 3);
    std::ifstream file(argv[2], std::ios::binary | std::ios::ate);
    require(bool(file));
    const auto bytes = file.tellg();
    require(bytes > 0 && bytes <= 16000 * 30 * 4 && bytes % 4 == 0);
    file.seekg(0);
    std::vector<float> audio(size_t(bytes) / 4);
    file.read(reinterpret_cast<char*>(audio.data()), bytes);
    require(bool(file));
    for (float value : audio) {
      require(std::isfinite(value) && std::abs(value) <= 1);
    }

    MoonshineStreamingModel model;
    const std::string tokenizer = std::string(argv[1]) + "/tokenizer.bin";
    require(model.load(argv[1], tokenizer.c_str(), 4) == 0);
    std::unique_ptr<MoonshineStreamingState> state(model.create_state());
    require(bool(state));
    int features = 0;
    int frames = 0;
    require(model.process_audio_chunk(state.get(), audio.data(), audio.size(),
                                      &features) == 0);
    require(model.encode(state.get(), true, &frames) == 0);
    // Do not score the upstream synthetic EOS fallback for empty memory.
    require(state->memory_len > 0);
    const int vocabulary = model.config.vocab_size;
    require(vocabulary > 0 && vocabulary <= 100000);

    std::vector<float> row(vocabulary);
    std::vector<int> tokens;
    std::vector<double> scores;
    int input = model.config.bos_id;
    bool eos = false;
    for (int step = 0; step < 128; ++step) {
      require(model.decode_step(state.get(), input, row.data()) == 0);
      const int token = best(row.data(), vocabulary);
      if (token == model.config.eos_id) {
        eos = true;
        break;
      }
      tokens.push_back(token);
      scores.push_back(probability(row.data(), vocabulary, token));
      input = token;
    }
    require(eos && !tokens.empty());

    model.decoder_reset(state.get());
    std::vector<int> draft{model.config.bos_id};
    draft.insert(draft.end(), tokens.begin(), tokens.end());
    std::vector<float> logits(draft.size() * vocabulary);
    require(model.decode_tokens(state.get(), draft.data(), draft.size(),
                                logits.data()) == 0);
    double draft_sum = 0;
    double max_delta = 0;
    for (size_t index = 0; index < tokens.size(); ++index) {
      const float* draft_row = logits.data() + index * vocabulary;
      require(best(draft_row, vocabulary) == tokens[index]);
      const double value = probability(draft_row, vocabulary, tokens[index]);
      draft_sum += value;
      max_delta = std::max(max_delta, std::abs(value - scores[index]));
    }
    // Batched and single-step probabilities are measured independently.
    // Token agreement does not establish probability equivalence.
    model.decoder_reset(state.get());
    draft[1] = (tokens[0] + 1) % vocabulary;
    require(model.decode_tokens(state.get(), draft.data(), draft.size(),
                                logits.data()) == 0);
    require(best(logits.data(), vocabulary) != draft[1]);

    double sum = 0;
    double log_sum = 0;
    double minimum = 1;
    double maximum = 0;
    for (double value : scores) {
      sum += value;
      log_sum += std::log(value);
      minimum = std::min(minimum, value);
      maximum = std::max(maximum, value);
    }
    std::printf(
        "{\"status\":\"DIAGNOSTIC_ONLY\",\"tokens\":%zu,"
        "\"mean_probability\":%.9g,\"geometric_mean\":%.9g,"
        "\"minimum\":%.9g,\"maximum\":%.9g,\"draft_verified\":true,"
        "\"draft_mean_probability\":%.9g,\"max_probability_delta\":%.9g,"
        "\"corrupted_draft_rejected\":true,\"calibrated\":false}\n",
        tokens.size(), sum / scores.size(), std::exp(log_sum / scores.size()),
        minimum, maximum, draft_sum / scores.size(), max_delta);
    return 0;
  } catch (const std::exception&) {
    std::fprintf(stderr, "confidence probe failed\n");
    return 1;
  }
}
