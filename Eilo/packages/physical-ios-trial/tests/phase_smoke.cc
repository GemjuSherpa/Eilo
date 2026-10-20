// Explicit local fixed-input smoke only. Caller verifies model SHA-256 before invocation.
#include "eilo_llm.h"
#include "eilo_trial_metrics.h"
#include <cmath>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <cstdio>
int main(int argc,char **argv){
  if(argc!=2)return 2;
  int fd=open(argv[1],O_RDONLY|O_NOFOLLOW);if(fd<0)return 2;
  EiloLlm *h=eilo_llm_create();if(!h){close(fd);return 2;}
  int status=eilo_llm_load(h,fd,2);close(fd);
  if(status!=EILO_LLM_DONE){eilo_llm_destroy(h);return 3;}
  const char prompt[]="<|im_start|>user\nSay hello.\n<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n";
  if(eilo_llm_count_tokens(h,prompt,std::strlen(prompt))<1 || eilo_llm_begin(h,prompt,std::strlen(prompt),8)!=EILO_LLM_DONE){eilo_llm_destroy(h);return 4;}
  char output[1024]{};int32_t bytes=0;int pieces=0;
  while((status=eilo_llm_next(h,output,sizeof(output),&bytes))==EILO_LLM_TOKEN){
    if(bytes<1 || bytes>1024 || ++pieces>8){eilo_llm_destroy(h);return 5;}
    std::memset(output,0,sizeof(output));
  }
  eilo_llm_destroy(h);std::memset(output,0,sizeof(output));
  if(status!=EILO_LLM_DONE || pieces<1)return 6;
  double metrics[7]{};
  if(eilo_trial_phase_metrics(metrics,7)!=1)return 7;
  for(double v:metrics)if(!std::isfinite(v) || v<0)return 8;
  if(metrics[5]<metrics[1]+metrics[2]+metrics[3]+metrics[4] || metrics[6]<metrics[5])return 9;
  std::printf("Pinned candidate native phase timing/generation PASS; pieces=%d; no output content exported\n",pieces);
}
