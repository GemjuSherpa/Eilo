#include "moonshine-streaming-model.h"
#include "score_trace.h"
#include "json.h"
#include <cstdio>
#include <fstream>
#include <memory>
#include <cstdlib>

using nlohmann::json;
static void need(bool v){if(!v)throw std::runtime_error("unavailable");}
static json unavailable(const char* source,const char* reason){return {{"source",source},{"status","UNAVAILABLE"},{"reason",reason}};}
// Text is sent only over the invocation pipe to the offline scoring parent. The
// runner scores in memory and never writes hypotheses/references to reports.
static json collect(MoonshineStreamingModel& model,MoonshineStreamingState* state,
 const std::vector<int>& draft,const char* source,std::vector<int>& accepted){
 model.decoder_reset(state);EiloScoreTrace trace;int* out=nullptr;int length=0;
 int result=model.decode_full(state,draft.empty()?nullptr:draft.data(),int(draft.size()),&out,&length,nullptr,&trace);
 std::unique_ptr<int,decltype(&std::free)> held(out,&std::free);
 if(result || !trace.available){need(out==nullptr && length==0 && trace.tokens.empty() && trace.scores.empty());return unavailable(source,trace.ended_eos?"EOS_WITHOUT_USABLE_SCORES":(std::string(trace.unavailable_reason)=="NO_EOS_OR_OUTPUT_CAP"?"NO_EOS_OR_OUTPUT_CAP":"INCOMPLETE_DECODE"));}
 need(out && length>0 && length<=128 && trace.tokens==std::vector<int>(out,out+length) && trace.scores.size()==size_t(length));
 need(trace.ended_eos && trace.max_oracle_error<=1e-10);
 double sum=0,logs=0,minimum=1;int greedy=0,verified=0,redecoded=0;
 for(auto score:trace.scores){need(std::isfinite(score.probability) && score.probability>0 && score.probability<=1);sum+=score.probability;logs+=std::log(score.probability);minimum=std::min(minimum,score.probability);greedy+=score.path==EiloScoreTrace::GREEDY;verified+=score.path==EiloScoreTrace::DRAFT;redecoded+=score.path==EiloScoreTrace::REDECODE;}
 std::vector<int64_t> tokens(out,out+length);std::string text=model.tokens_to_text(tokens);need(!text.empty() && text.size()<=4096);
 accepted.assign(out,out+length);
 return {{"source",source},{"status","AVAILABLE"},{"transcript",text},{"tokens",length},
  {"confidence",sum/length},{"geometric_mean",std::exp(logs/length)},{"minimum",minimum},
  {"oracle_error",trace.max_oracle_error},{"origins",{{"greedy",greedy},{"verification",verified},{"redecode",redecoded}}}};
}
int main(int argc,char** argv){
 try{
  need(argc==3);std::ifstream file(argv[2],std::ios::binary|std::ios::ate);need(bool(file));auto bytes=file.tellg();
  need(bytes>0 && bytes<=16000*30*4 && bytes%4==0);file.seekg(0);std::vector<float> audio(size_t(bytes)/4);file.read(reinterpret_cast<char*>(audio.data()),bytes);need(bool(file));
  for(float x:audio)need(std::isfinite(x) && std::abs(x)<=1);
  MoonshineStreamingModel model;const std::string tokenizer=std::string(argv[1])+"/tokenizer.bin";need(model.load(argv[1],tokenizer.c_str(),4)==0);
  std::unique_ptr<MoonshineStreamingState> state(model.create_state());need(bool(state));
  int features=0,frames=0;need(model.process_audio_chunk(state.get(),audio.data(),audio.size(),&features)==0);need(model.encode(state.get(),true,&frames)==0);
  std::vector<int> greedy_tokens,unused;
  auto greedy=collect(model,state.get(),{},"GREEDY_PREBIAS_MEAN_V1",greedy_tokens);
  auto draft=greedy_tokens.empty()?unavailable("SELF_DRAFT_PREBIAS_MEAN_V1","GREEDY_UNAVAILABLE"):
    collect(model,state.get(),greedy_tokens,"SELF_DRAFT_PREBIAS_MEAN_V1",unused);
  const auto response=json{{"schema_version",1},{"paths",json::array({greedy,draft})}}.dump();
  need(response.size()<=32768);std::puts(response.c_str());return 0;
 }catch(const std::exception&){std::fprintf(stderr,"corpus score collector unavailable\n");return 1;}
}
