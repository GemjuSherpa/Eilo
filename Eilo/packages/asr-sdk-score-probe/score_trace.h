#pragma once
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

// Invocation-only diagnostics. No text, calibration, policy or shipping ABI.
struct EiloScoreTrace {
  enum Path { GREEDY, DRAFT, REDECODE };
  struct Score { double probability; Path path; };
  int fail_decoder_call=0, empty_decoder_call=0, nan_decoder_call=0, output_cap=0;
  bool fail_allocation=false;
  int decoder_calls=0, biased_choices=0;
  bool available=false, ended_eos=false;
  double max_oracle_error=0;
  std::vector<int> tokens;
  std::vector<Score> scores;
  void begin(){decoder_calls=0;biased_choices=0;available=false;ended_eos=false;max_oracle_error=0;tokens.clear();scores.clear();}
  void discard(){available=false;tokens.clear();scores.clear();}
  struct Guard {
    EiloScoreTrace* trace;
    ~Guard(){if(trace && !trace->available)trace->discard();}
  };
  Score measure(const std::vector<float>& raw,int selected,Path path){
    if(raw.empty() || selected<0 || selected>=int(raw.size()))throw std::runtime_error("unavailable");
    double maximum=-std::numeric_limits<double>::infinity();
    for(float x:raw){if(!std::isfinite(x))throw std::runtime_error("unavailable");maximum=std::max(maximum,double(x));}
    double total=0;for(float x:raw)total+=std::exp(double(x)-maximum);
    double value=std::exp(double(raw[selected])-maximum)/total;
    // Independent long-double oracle uses the captured pre-bias row, not a
    // different decode path. No assumption of step/batch numerical equivalence.
    long double sum=0;for(float x:raw)sum+=std::exp(static_cast<long double>(x)-maximum);
    const long double reference=std::exp(static_cast<long double>(raw[selected])-maximum)/sum;
    max_oracle_error=std::max(max_oracle_error,double(std::abs(reference-value)));
    if(!std::isfinite(value) || value<=0 || value>1)throw std::runtime_error("unavailable");
    return {value,path};
  }
  void accept(int token,Score score,int bos,int eos,int cap){
    if(token==bos || token==eos || int(tokens.size())>=cap)throw std::runtime_error("unavailable");
    tokens.push_back(token);scores.push_back(score);
  }
};
