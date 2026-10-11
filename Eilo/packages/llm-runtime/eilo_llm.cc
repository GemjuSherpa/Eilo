#include "eilo_llm.h"
#include "llama.h"
#include <array>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <exception>
#include <memory>
#include <mutex>
#include <sys/stat.h>
#include <unistd.h>

namespace {
constexpr int kContext = 4096, kBatch = 128, kPiece = 1024;
constexpr int64_t kModelBytes = 1282439424;
void wipe(void *data, size_t bytes) {
  auto *p = static_cast<volatile unsigned char *>(data);
  while (bytes--) *p++ = 0;
}
void quiet_log(ggml_log_level, const char *, void *) {}
void quiet_abort(const char *) {}
std::once_flag backend_once;
struct Tokens {
  std::array<llama_token, kContext> data{};
  ~Tokens() { wipe(data.data(), sizeof(data)); }
};
struct Piece {
  std::array<char, kPiece> data{};
  ~Piece() { wipe(data.data(), sizeof(data)); }
};
}

struct EiloLlm {
  enum class State { created, loaded, running, done, failed } state = State::created;
  std::atomic<bool> cancelled{false};
  llama_model *model = nullptr;
  llama_context *context = nullptr;
  llama_sampler *sampler = nullptr;
  llama_batch_ext *batch = nullptr;
  int position = 0, generated = 0, limit = 0, threads = 0;

  void clear() {
    if (batch) { llama_batch_ext_free(batch); batch = nullptr; }
    if (sampler) { llama_sampler_free(sampler); sampler = nullptr; }
    if (context) {
      // Zero the KV cache before freeing it. Vendor logits/allocator erasure is
      // a separate audit; do not treat this as a complete private-memory pass.
      llama_memory_clear(llama_get_memory(context), true);
      llama_free(context); context = nullptr;
    }
    if (model) { llama_model_free(model); model = nullptr; }
  }
  ~EiloLlm() { clear(); }
  int32_t stop(int32_t reason) {
    clear(); state = reason == EILO_LLM_DONE ? State::done : State::failed;
    return reason;
  }
  bool stopped() const { return cancelled.load(std::memory_order_acquire); }
  static bool abort(void *data) { return static_cast<EiloLlm *>(data)->stopped(); }
  static bool progress(float, void *data) { return !abort(data); }
  bool decode(const llama_token *tokens, int count) {
    llama_batch_ext_clear(batch);
    for (int i = 0; i < count; ++i) {
      int index = llama_batch_ext_add_token(batch, 0, tokens[i]);
      llama_pos pos = position + i;
      if (index < 0 || !llama_batch_ext_set_pos(batch, index, &pos) ||
          !llama_batch_ext_set_output_logits(batch, index, i == count - 1)) return false;
    }
    if (llama_process(context, LLAMA_PROCESS_TYPE_DECODE, batch) != 0) return false;
    position += count;
    return true;
  }
};

extern "C" EiloLlm *eilo_llm_create() {
  try { return new EiloLlm; } catch (...) { return nullptr; }
}

extern "C" int32_t eilo_llm_load(EiloLlm *h, int32_t fd, int32_t threads) {
  if (!h) return EILO_LLM_INVALID;
  if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
  if (h->state != EiloLlm::State::created) return h->stop(EILO_LLM_INVALID);
  try {
    struct stat info{};
    if (fd < 0 || threads < 1 || threads > 8 || fstat(fd, &info) != 0 ||
        !S_ISREG(info.st_mode) || info.st_size != kModelBytes) return h->stop(EILO_LLM_INVALID);
    int copy = dup(fd);
    if (copy < 0) return h->stop(EILO_LLM_UNAVAILABLE);
    FILE *file = fdopen(copy, "rb");
    if (!file) { close(copy); return h->stop(EILO_LLM_UNAVAILABLE); }
    std::unique_ptr<FILE, decltype(&fclose)> owned(file, fclose);
    if (fseek(file, 0, SEEK_SET) != 0) return h->stop(EILO_LLM_UNAVAILABLE);
    std::call_once(backend_once, [] {
      // llama/ggml logging is process-wide. Do not log prompts, paths or tokens.
      llama_log_set(quiet_log, nullptr);
      ggml_log_set(quiet_log, nullptr);
      llama_backend_init();
      // Preserve fatal termination without publishing a vendor message/backtrace
      // or attaching a debugger. These hooks are also process-wide.
      ggml_set_abort_callback(quiet_abort);
      std::set_terminate([] { std::abort(); });
    });
    auto params = llama_model_default_params();
    ggml_backend_dev_t no_offload[] = {nullptr};
    params.devices = no_offload;
    params.n_gpu_layers = 0;
    params.split_mode = LLAMA_SPLIT_MODE_NONE;
    params.load_mode = LLAMA_LOAD_MODE_MMAP;
    params.progress_callback = EiloLlm::progress;
    params.progress_callback_user_data = h;
    params.use_extra_bufts = false;
    params.no_host = false;
    params.no_alloc = false;
    params.vocab_only = false;
    params.load_mtp = false;
    h->model = llama_model_load_from_file_ptr(file, params);
    if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
    if (!h->model) return h->stop(EILO_LLM_UNAVAILABLE);
    char architecture[32]{}, quantization[32]{};
    if (llama_model_meta_val_str(h->model, "general.architecture", architecture, sizeof(architecture)) != 5 ||
        std::strcmp(architecture, "qwen3") != 0 ||
        llama_model_meta_val_str(h->model, "general.file_type", quantization, sizeof(quantization)) != 2 ||
        std::strcmp(quantization, "15") != 0 || llama_model_has_encoder(h->model) ||
        !llama_model_has_decoder(h->model)) return h->stop(EILO_LLM_UNAVAILABLE);
    h->threads = threads; h->state = EiloLlm::State::loaded;
    return EILO_LLM_DONE;
  } catch (...) { return h->stop(EILO_LLM_UNAVAILABLE); }
}

extern "C" int32_t eilo_llm_begin(EiloLlm *h, const char *prompt, int32_t bytes, int32_t limit) {
  if (!h) return EILO_LLM_INVALID;
  if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
  if (h->state != EiloLlm::State::loaded || !prompt || bytes < 1 || bytes > 16384 ||
      limit < 1 || limit > 256 || std::memchr(prompt, 0, bytes)) return h->stop(EILO_LLM_INVALID);
  try {
    Tokens tokens;
    auto *vocab = llama_model_get_vocab(h->model);
    int count = llama_tokenize(vocab, prompt, bytes, tokens.data.data(), kContext, true, true);
    if (count < 1 || count > kContext - limit) return h->stop(EILO_LLM_INVALID);
    if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
    auto params = llama_context_default_params();
    params.n_ctx = kContext; params.n_batch = kBatch; params.n_ubatch = kBatch;
    params.n_seq_max = 1; params.n_threads = h->threads; params.n_threads_batch = h->threads;
    params.offload_kqv = false; params.op_offload = false; params.embeddings = false;
    params.no_perf = true; params.abort_callback = EiloLlm::abort; params.abort_callback_data = h;
    h->context = llama_init_from_model(h->model, params);
    if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
    if (!h->context || llama_n_ctx(h->context) != kContext) return h->stop(EILO_LLM_UNAVAILABLE);
    h->sampler = llama_sampler_init_greedy();
    h->batch = llama_batch_ext_init(h->context);
    if (!h->sampler || !h->batch) return h->stop(EILO_LLM_UNAVAILABLE);
    for (int offset = 0; offset < count; offset += kBatch) {
      int size = count - offset < kBatch ? count - offset : kBatch;
      if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
      bool ok = h->decode(tokens.data.data() + offset, size);
      if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
      if (!ok) return h->stop(EILO_LLM_UNAVAILABLE);
    }
    h->limit = limit; h->state = EiloLlm::State::running;
    return EILO_LLM_DONE;
  } catch (...) { return h->stop(EILO_LLM_UNAVAILABLE); }
}

extern "C" int32_t eilo_llm_next(EiloLlm *h, char *out, int32_t capacity, int32_t *bytes) {
  if (bytes) *bytes = 0;
  if (out && capacity == kPiece) wipe(out, kPiece);
  if (!h) return EILO_LLM_INVALID;
  if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
  if (h->state == EiloLlm::State::done) return EILO_LLM_DONE;
  if (h->state != EiloLlm::State::running || !out || capacity != kPiece || !bytes)
    return h->stop(EILO_LLM_INVALID);
  try {
    if (h->generated >= h->limit) return h->stop(EILO_LLM_DONE);
    auto *vocab = llama_model_get_vocab(h->model);
    llama_token token = llama_sampler_sample(h->sampler, h->context, -1);
    if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
    if (llama_vocab_is_eog(vocab, token)) return h->stop(EILO_LLM_DONE);
    Piece piece;
    int size = llama_token_to_piece(vocab, token, piece.data.data(), kPiece, 0, false);
    if (size < 0 || size > kPiece) return h->stop(EILO_LLM_UNAVAILABLE);
    // Decode before copying: cancellation/failure releases no piece from this step.
    if (h->generated + 1 < h->limit) {
      bool ok = h->decode(&token, 1);
      if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
      if (!ok) return h->stop(EILO_LLM_UNAVAILABLE);
    }
    if (h->stopped()) return h->stop(EILO_LLM_CANCELLED);
    std::memcpy(out, piece.data.data(), size); *bytes = size; ++h->generated;
    return EILO_LLM_TOKEN;
  } catch (...) { return h->stop(EILO_LLM_UNAVAILABLE); }
}

extern "C" void eilo_llm_cancel(EiloLlm *h) {
  if (h) h->cancelled.store(true, std::memory_order_release);
}
extern "C" void eilo_llm_destroy(EiloLlm *h) { delete h; }
