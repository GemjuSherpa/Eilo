#include "eilo_llm.h"
#include "llama.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"contract failure at line %d\n",__LINE__); std::exit(1); } } while (0)
// Implement the actual pinned C API with a scripted backend. This tests Eilo's
// lifecycle/error boundaries, not model quality or real vendor buffer erasure.
struct llama_model {};
struct llama_context {};
struct llama_batch_ext {};
struct llama_vocab {};
struct llama_memory_i {};
static llama_vocab vocab;
static llama_memory_i memory;
static EiloLlm *current;
static llama_context_params context_params;
static int live = 0, processes = 0, samples = 0, token_count = 300;
static bool cancel_load = false, cancel_decode = false, cancel_sample = false;
static bool fail_load = false, fail_context = false, fail_decode = false, oversized = false;
static bool wrong_arch = false, wrong_quant = false, end_token = false, throw_load = false;

void llama_backend_init() {}
void llama_log_set(ggml_log_callback, void *) {}
void ggml_log_set(ggml_log_callback, void *) {}
ggml_abort_callback_t ggml_set_abort_callback(ggml_abort_callback_t callback) {
  CHECK(callback); callback("synthetic private cause must not escape"); return nullptr;
}
llama_model_params llama_model_default_params() { return {}; }
llama_context_params llama_context_default_params() { return {}; }
llama_model *llama_model_load_from_file_ptr(FILE *, llama_model_params p) {
  CHECK(p.devices && p.devices[0] == nullptr && p.n_gpu_layers == 0);
  CHECK(!p.use_extra_bufts && !p.vocab_only && !p.no_alloc && !p.load_mtp);
  if (throw_load) throw std::runtime_error("synthetic cause must not escape");
  if (cancel_load) eilo_llm_cancel(current);
  if (!p.progress_callback(0.5f, p.progress_callback_user_data) || fail_load) return nullptr;
  ++live; return new llama_model;
}
void llama_model_free(llama_model *m) { --live; delete m; }
int32_t llama_model_meta_val_str(const llama_model *, const char *key, char *out, size_t size) {
  const char *value = std::strcmp(key,"general.architecture") == 0 ? (wrong_arch ? "other" : "qwen3") : (wrong_quant ? "14" : "15");
  CHECK(std::strlen(value) < size); std::strcpy(out,value); return static_cast<int32_t>(std::strlen(value));
}
bool llama_model_has_encoder(const llama_model *) { return false; }
bool llama_model_has_decoder(const llama_model *) { return true; }
const llama_vocab *llama_model_get_vocab(const llama_model *) { return &vocab; }
int32_t llama_tokenize(const llama_vocab *, const char *, int32_t, llama_token *out, int32_t cap, bool, bool) {
  if (token_count > cap) return -token_count;
  for (int i=0;i<token_count;++i) out[i]=i+1;
  return token_count;
}
llama_context *llama_init_from_model(llama_model *, llama_context_params p) {
  CHECK(p.n_ctx == 4096 && p.n_batch == 128 && p.n_ubatch == 128);
  CHECK(p.n_threads == 2 && p.n_threads_batch == 2 && !p.offload_kqv && !p.op_offload && !p.embeddings);
  if (fail_context) return nullptr;
  context_params = p; ++live; return new llama_context;
}
uint32_t llama_n_ctx(const llama_context *) { return 4096; }
llama_memory_t llama_get_memory(const llama_context *) { return &memory; }
void llama_memory_clear(llama_memory_t, bool zero) { CHECK(zero); }
void llama_free(llama_context *c) { --live; delete c; }
llama_sampler *llama_sampler_init_greedy() { ++live; return new llama_sampler; }
void llama_sampler_free(llama_sampler *s) { --live; delete s; }
llama_batch_ext *llama_batch_ext_init(llama_context *) { ++live; return new llama_batch_ext; }
void llama_batch_ext_free(llama_batch_ext *b) { --live; delete b; }
void llama_batch_ext_clear(llama_batch_ext *) {}
int32_t llama_batch_ext_add_token(llama_batch_ext *, llama_seq_id, llama_token) { return 0; }
bool llama_batch_ext_set_pos(llama_batch_ext *, int32_t, const llama_pos *) { return true; }
bool llama_batch_ext_set_output_logits(llama_batch_ext *, int32_t, bool) { return true; }
int32_t llama_process(llama_context *, llama_process_type type, llama_batch_ext *) {
  CHECK(type == LLAMA_PROCESS_TYPE_DECODE); ++processes;
  if (cancel_decode) eilo_llm_cancel(current);
  return context_params.abort_callback(context_params.abort_callback_data) ? 2 : (fail_decode ? -2 : 0);
}
llama_token llama_sampler_sample(llama_sampler *, llama_context *, int32_t) {
  ++samples; if (cancel_sample) eilo_llm_cancel(current); return end_token ? 99 : 1;
}
bool llama_vocab_is_eog(const llama_vocab *, llama_token token) { return token == 99; }
int32_t llama_token_to_piece(const llama_vocab *, llama_token, char *out, int32_t size, int32_t, bool special) {
  CHECK(size == 1024 && !special); std::memset(out,'x',size); return oversized ? -1025 : 2;
}

static void reset() {
  CHECK(live == 0); processes=0; samples=0; token_count=300;
  cancel_load=cancel_decode=cancel_sample=fail_load=fail_context=fail_decode=oversized=false;
  wrong_arch=wrong_quant=end_token=throw_load=false;
  current=eilo_llm_create(); CHECK(current);
}
static void finish() { eilo_llm_destroy(current); current=nullptr; CHECK(live == 0); }
static void loaded(int fd) { CHECK(eilo_llm_load(current,fd,2)==0); }
static void begun(int fd, int limit=2) { loaded(fd); CHECK(eilo_llm_begin(current,"fixture",7,limit)==0); }
static int next() {
  char out[1024]; std::memset(out,'s',sizeof(out)); int bytes=55;
  int result=eilo_llm_next(current,out,sizeof(out),&bytes);
  if (result!=EILO_LLM_TOKEN) { CHECK(bytes==0); for(char c:out) CHECK(c==0); }
  else CHECK(bytes==2 && out[0]=='x' && out[2]==0);
  return result;
}
int main() {
  FILE *file=std::tmpfile(); CHECK(file); int fd=fileno(file); CHECK(ftruncate(fd,1282439424)==0);
  int scenarios=0;
  reset(); eilo_llm_cancel(current); CHECK(eilo_llm_load(current,fd,2)==-2); CHECK(next()==-2); finish(); ++scenarios;
  reset(); cancel_load=true; CHECK(eilo_llm_load(current,fd,2)==-2); finish(); ++scenarios;
  reset(); fail_load=true; CHECK(eilo_llm_load(current,fd,2)==-3); CHECK(next()==-1); finish(); ++scenarios;
  reset(); throw_load=true; CHECK(eilo_llm_load(current,fd,2)==-3); finish(); ++scenarios;
  reset(); wrong_arch=true; CHECK(eilo_llm_load(current,fd,2)==-3); finish(); ++scenarios;
  reset(); wrong_quant=true; CHECK(eilo_llm_load(current,fd,2)==-3); finish(); ++scenarios;
  reset(); CHECK(eilo_llm_load(current,-1,2)==-1); finish(); ++scenarios;
  reset(); CHECK(eilo_llm_load(current,fd,9)==-1); finish(); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_load(current,fd,2)==-1); finish(); ++scenarios;
  reset(); loaded(fd); token_count=4097; CHECK(eilo_llm_begin(current,"fixture",7,2)==-1); finish(); ++scenarios;
  reset(); loaded(fd); token_count=4095; CHECK(eilo_llm_begin(current,"fixture",7,2)==-1); finish(); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_begin(current,"x\0x",3,2)==-1); finish(); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_begin(current,"fixture",16385,2)==-1); finish(); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_begin(current,"fixture",7,257)==-1); finish(); ++scenarios;
  reset(); loaded(fd); fail_context=true; CHECK(eilo_llm_begin(current,"fixture",7,2)==-3); finish(); ++scenarios;
  reset(); loaded(fd); cancel_decode=true; CHECK(eilo_llm_begin(current,"fixture",7,2)==-2); CHECK(processes==1); finish(); ++scenarios;
  reset(); loaded(fd); fail_decode=true; CHECK(eilo_llm_begin(current,"fixture",7,2)==-3); finish(); ++scenarios;
  reset(); begun(fd); CHECK(processes==3); CHECK(next()==1); CHECK(next()==1); CHECK(next()==0); CHECK(next()==0); CHECK(samples==2); CHECK(live==0); finish(); ++scenarios;
  reset(); begun(fd); end_token=true; CHECK(next()==0); CHECK(next()==0); CHECK(samples==1); finish(); ++scenarios;
  reset(); begun(fd); oversized=true; CHECK(next()==-3); CHECK(next()==-1); finish(); ++scenarios;
  reset(); begun(fd); cancel_decode=true; CHECK(next()==-2); finish(); ++scenarios;
  reset(); begun(fd); cancel_sample=true; CHECK(next()==-2); finish(); ++scenarios;
  reset(); begun(fd); fail_decode=true; CHECK(next()==-3); finish(); ++scenarios;
  reset(); begun(fd); eilo_llm_cancel(current); CHECK(next()==-2); CHECK(eilo_llm_begin(current,"fixture",7,2)==-2); finish(); ++scenarios;
  reset(); begun(fd); char out[1024]; int bytes=9; CHECK(eilo_llm_next(current,out,1023,&bytes)==-1 && bytes==0); CHECK(live==0); finish(); ++scenarios;
  reset(); CHECK(eilo_llm_begin(current,"fixture",7,2)==-1); finish(); ++scenarios;
  CHECK(eilo_llm_next(nullptr,nullptr,0,nullptr)==-1); eilo_llm_cancel(nullptr); eilo_llm_destroy(nullptr); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_count_tokens(current,"fixture",7)==300); CHECK(eilo_llm_count_tokens(current,"fixture",7)==300); CHECK(eilo_llm_begin(current,"fixture",7,2)==0); finish(); ++scenarios;
  reset(); loaded(fd); token_count=4097; CHECK(eilo_llm_count_tokens(current,"fixture",7)==4097); token_count=300; CHECK(eilo_llm_begin(current,"fixture",7,2)==0); finish(); ++scenarios;
  reset(); loaded(fd); eilo_llm_cancel(current); CHECK(eilo_llm_count_tokens(current,"fixture",7)==-2); finish(); ++scenarios;
  reset(); loaded(fd); CHECK(eilo_llm_count_tokens(current,"x\0x",3)==-1); finish(); ++scenarios;
  std::fclose(file); std::printf("%d scripted C ABI lifecycle scenarios PASS\n",scenarios);
}
