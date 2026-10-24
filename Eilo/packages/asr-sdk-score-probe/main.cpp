#include "moonshine-streaming-model.h"
#include "context-biaser.h"
#include "score_trace.h"
#include <cstdio>
#include <fstream>
#include <memory>
#include <cstdlib>

static void require(bool v){if(!v)throw std::runtime_error("unavailable");}
static std::vector<int> decode(MoonshineStreamingModel& model,MoonshineStreamingState* state,
 const std::vector<int>& draft,EiloScoreTrace* scores=nullptr,ContextBiaser* bias=nullptr){
 model.decoder_reset(state);int* out=nullptr;int length=0;
 int err=model.decode_full(state,draft.empty()?nullptr:draft.data(),int(draft.size()),&out,&length,bias,scores);
 std::unique_ptr<int,decltype(&std::free)> held(out,&std::free);
 if(scores && !scores->available){require(out==nullptr && length==0 && scores->tokens.empty() && scores->scores.empty());return {};}
 require(err==0 && out && length>0 && length<128);return {out,out+length};
}
static void check_path(MoonshineStreamingModel& model,MoonshineStreamingState* state,
 const std::vector<int>& draft,int expected_draft,bool divergence,ContextBiaser* bias=nullptr){
 const auto baseline=decode(model,state,draft,nullptr,bias);
 EiloScoreTrace trace;const auto scored=decode(model,state,draft,&trace,bias);
 require(trace.available && baseline==scored && trace.tokens==scored && trace.max_oracle_error<1e-10);
 int accepted=0,redecoded=0;double sum=0,minimum=1;
 for(auto score:trace.scores){accepted+=score.path==EiloScoreTrace::DRAFT;redecoded+=score.path==EiloScoreTrace::REDECODE;sum+=score.probability;minimum=std::min(minimum,score.probability);}
 require(accepted==expected_draft && (redecoded>0)==divergence);
 if(bias)require(trace.biased_choices>0);
 std::printf("{\"mode\":\"%s\",\"tokens\":%zu,\"accepted_draft\":%d,\"redecoded\":%d,\"mean_probability\":%.9g,\"minimum\":%.9g,\"oracle_max_error\":%.9g,\"baseline_tokens_equal\":true,\"biased_choices\":%d}\n",
 bias?"biased":(draft.empty()?"greedy":(divergence?(expected_draft?"late_divergence":"early_divergence"):"accepted_draft")),scored.size(),accepted,redecoded,sum/scored.size(),minimum,trace.max_oracle_error,trace.biased_choices);
}
int main(int argc,char** argv){
 const char* stage="input";
 try{
  require(argc==3);std::ifstream file(argv[2],std::ios::binary|std::ios::ate);require(bool(file));auto bytes=file.tellg();
  require(bytes>0 && bytes<=16000*30*4 && bytes%4==0);file.seekg(0);std::vector<float> audio(size_t(bytes)/4);file.read(reinterpret_cast<char*>(audio.data()),bytes);require(bool(file));
  for(float x:audio)require(std::isfinite(x) && std::abs(x)<=1);
  MoonshineStreamingModel model;const std::string tokenizer=std::string(argv[1])+"/tokenizer.bin";
  require(model.load(argv[1],tokenizer.c_str(),4)==0);std::unique_ptr<MoonshineStreamingState> state(model.create_state());require(bool(state));
  int features=0,frames=0;require(model.process_audio_chunk(state.get(),audio.data(),audio.size(),&features)==0);require(model.encode(state.get(),true,&frames)==0);require(state->memory_len>0);
  auto greedy=decode(model,state.get(),{});require(greedy.size()>1);
  stage="greedy";check_path(model,state.get(),{},0,false);
  stage="accepted_draft";check_path(model,state.get(),greedy,int(greedy.size()),false);
  auto corrupted=greedy;
  auto corrupt=[&](int token){int t=(token+1)%model.config.vocab_size;while(t==model.config.bos_id || t==model.config.eos_id)t=(t+1)%model.config.vocab_size;return t;};
  corrupted[0]=corrupt(corrupted[0]);stage="early_divergence";check_path(model,state.get(),corrupted,0,true);
  corrupted=greedy;corrupted.back()=corrupt(corrupted.back());stage="late_divergence";check_path(model,state.get(),corrupted,int(greedy.size()-1),true);
  // A genuine SDK ContextBiaser changes the first selection. Score verification
  // still uses each exact unmodified row captured before ContextBiaser::apply.
  model.decoder_reset(state.get());std::vector<float> row(model.config.vocab_size);require(model.decode_step(state.get(),model.config.bos_id,row.data())==0);
  int first=int(std::max_element(row.begin(),row.end())-row.begin()),second=-1;
  for(int i=0;i<int(row.size());++i)if(i!=first && i!=model.config.bos_id && i!=model.config.eos_id && (second<0 || row[i]>row[second]))second=i;
  require(second>=0);ContextBiaser bias;bias.add_token_sequence({second});bias.set_boost(row[first]-row[second]+0.05f);
  stage="biased";check_path(model,state.get(),{},0,false,&bias);
  stage="faults";const int original_memory=state->memory_len;state->memory_len=0;EiloScoreTrace empty;require(decode(model,state.get(),{},&empty).empty() && !empty.available);state->memory_len=original_memory;
  int unavailable=1;
  for(int mode=0;mode<6;++mode){
   EiloScoreTrace trace;
   if(mode==0)trace.fail_decoder_call=1;
   if(mode==1)trace.fail_decoder_call=2;
   if(mode==2)trace.empty_decoder_call=1;
   if(mode==3)trace.nan_decoder_call=1;
   if(mode==4)trace.output_cap=1;
   if(mode==5)trace.fail_allocation=true;
   require(decode(model,state.get(),{},&trace).empty() && !trace.available);++unavailable;
  }
  std::printf("{\"fault_cases_unavailable\":%d,\"usable_partial_scores\":0,\"calibrated\":false,\"policy_authorized\":false}\n",unavailable);
  return 0;
 }catch(const std::exception&){std::fprintf(stderr,"SDK score probe unavailable: %s\n",stage);return 1;}
}
