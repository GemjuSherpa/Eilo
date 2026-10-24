"""Reviewable local-only instrumentation of pinned SDK decode_full; never edits the cache."""
from pathlib import Path
import hashlib
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'asr-confidence-probe'))
from check_android import verify_source


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('upstream overlay anchor mismatch')
    return text.replace(old,new)


def generate(source,output):
    verify_source(source)
    output.mkdir(parents=True,exist_ok=False)
    header=(source/'core/moonshine-streaming-model.h').read_text()
    header='#include "score_trace.h"\n'+header
    header=once(header,'                  ContextBiaser *biaser = nullptr);','                  ContextBiaser *biaser = nullptr, EiloScoreTrace *scores = nullptr);')
    cpp=(source/'core/moonshine-streaming-model.cpp').read_text()
    start=cpp.index('int MoonshineStreamingModel::decode_full(');end=cpp.index('\nvoid MoonshineStreamingModel::decoder_reset',start)
    body=cpp[start:end]
    body=once(body,'ContextBiaser *biaser) {','''ContextBiaser *biaser, EiloScoreTrace *scores) {
  if(scores){scores->begin();if(tokens_out)*tokens_out=nullptr;if(tokens_len_out)*tokens_len_out=0;}
  EiloScoreTrace::Guard score_guard{scores};
  try {''')
    body=once(body,'  // Helper lambda for argmax','''  if(scores){
    if(config.vocab_size<=0 || config.vocab_size>100000 || speculative_len<0 || speculative_len>128)throw std::runtime_error("unavailable");
    if(speculative_len && !speculative_tokens)throw std::runtime_error("unavailable");
    for(int i=0;i<speculative_len;++i)if(speculative_tokens[i]<0 || speculative_tokens[i]>=config.vocab_size || speculative_tokens[i]==config.bos_id || speculative_tokens[i]==config.eos_id)throw std::runtime_error("unavailable");
    max_tokens=std::min(max_tokens,128);
    if(scores->output_cap>0)max_tokens=std::min(max_tokens,scores->output_cap);
  }
  EiloScoreTrace::Score last_score{0,EiloScoreTrace::GREEDY};
  EiloScoreTrace::Path score_path=EiloScoreTrace::GREEDY;
  // Helper lambda for argmax''')
    body=once(body,'  auto biased_argmax = [&](float *logits_row) -> int {','''  auto biased_argmax = [&](float *logits_row) -> int {
    std::vector<float> raw;
    if(scores)raw.assign(logits_row,logits_row+config.vocab_size);''')
    body=once(body,'    return argmax(logits_row);','''    int chosen=argmax(logits_row);
    if(scores){last_score=scores->measure(raw,chosen,score_path);if(argmax(raw.data())!=chosen)++scores->biased_choices;}
    return chosen;''')
    body=once(body,'  auto run_decoder = [this, state]','  auto run_decoder = [this, state, scores]')
    body=once(body,'    return run_decoder_with_cross_kv(state, tokens, logits);','''    if(scores && ++scores->decoder_calls==scores->fail_decoder_call){scores->unavailable_reason="DECODER_ERROR";return 1;}
    int result=run_decoder_with_cross_kv(state, tokens, logits);
    if(scores){
      if(scores->decoder_calls==scores->empty_decoder_call)logits.clear();
      if(scores->decoder_calls==scores->nan_decoder_call && !logits.empty())logits[0]=std::numeric_limits<float>::quiet_NaN();
      if(result || logits.size()!=tokens.size()*size_t(config.vocab_size)){scores->unavailable_reason="MISSING_LOGITS_OR_DECODER_ERROR";throw std::runtime_error("unavailable");}
    }
    return result;''')
    body=once(body,'    int current_token = start_token;','    int current_token = start_token;\n    auto current_score=last_score;')
    body=once(body,'      result_tokens.push_back(current_token);','''      result_tokens.push_back(current_token);
      if(scores)scores->accept(current_token,current_score,config.bos_id,config.eos_id,max_tokens);''')
    body=once(body,'      current_token = biased_argmax(logits.data());','''      score_path=EiloScoreTrace::GREEDY;
      current_token = biased_argmax(logits.data());
      current_score=last_score;''')
    body=once(body,'    }\n  };\n\n  if (speculative_tokens','    }\n    if(scores)scores->ended_eos=current_token==config.eos_id;\n  };\n\n  if (speculative_tokens')
    body=once(body,'    std::vector<int> predictions;','    std::vector<int> predictions;\n    std::vector<EiloScoreTrace::Score> prediction_scores;\n    score_path=EiloScoreTrace::DRAFT;')
    body=once(body,'      if (biaser != nullptr &&','      if(scores)prediction_scores.push_back(last_score);\n      if (biaser != nullptr &&')
    body=once(body,'      result_tokens.push_back(speculative_tokens[i]);','''      result_tokens.push_back(speculative_tokens[i]);
      if(scores)scores->accept(speculative_tokens[i],prediction_scores[i],config.bos_id,config.eos_id,max_tokens);''')
    body=once(body,'      continue_ar_decoding(final_pred);','      if(scores)last_score=prediction_scores[speculative_len];\n      continue_ar_decoding(final_pred);')
    body=once(body,'      int new_pred =','      score_path=EiloScoreTrace::REDECODE;\n      int new_pred =')
    body=once(body,'    if (*tokens_out == nullptr) {','    if (*tokens_out == nullptr) {\n      if(scores)*tokens_len_out=0;')
    body=once(body,'  // Allocate and copy output','''  if(scores && (!scores->ended_eos || result_tokens.empty() || scores->tokens!=result_tokens || scores->scores.size()!=result_tokens.size())){scores->unavailable_reason="NO_EOS_OR_OUTPUT_CAP";throw std::runtime_error("unavailable");}
  if(scores && scores->fail_allocation){scores->unavailable_reason="ALLOCATION_FAILURE";throw std::bad_alloc();}
  // Allocate and copy output''')
    body=once(body,'  return 0;\n}', '''  if(scores)scores->available=true;
  return 0;
  }catch(...){
    if(!scores)throw;
    if(tokens_out && *tokens_out){free(*tokens_out);*tokens_out=nullptr;}
    if(tokens_len_out)*tokens_len_out=0;
    return 1;
  }
}''')
    cpp=cpp[:start]+body+cpp[end:]
    (output/'moonshine-streaming-model.h').write_text(header)
    (output/'moonshine-streaming-model.cpp').write_text(cpp)
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}
