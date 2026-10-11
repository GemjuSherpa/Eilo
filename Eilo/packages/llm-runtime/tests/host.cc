#include "eilo_llm.h"
#include "ggml-backend.h"
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { std::fprintf(stderr,"native fixture failure at line %d\n",__LINE__); std::exit(1); } } while (0)
using Handle=std::unique_ptr<EiloLlm,decltype(&eilo_llm_destroy)>;
static Handle handle() { Handle h(eilo_llm_create(),eilo_llm_destroy); CHECK(h); return h; }
static void network_probe(int family,int type) {
  int fd=socket(family,type,0);
  if(fd<0) { CHECK(errno==EPERM || errno==EACCES); return; }
  int result;
  if(family==AF_INET) {
    sockaddr_in address{}; address.sin_family=AF_INET; address.sin_port=htons(9);
    address.sin_addr.s_addr=htonl(type==SOCK_STREAM ? 0x7f000001 : 0xcb007101);
    result=type==SOCK_STREAM ? connect(fd,reinterpret_cast<sockaddr *>(&address),sizeof(address)) :
      static_cast<int>(sendto(fd,"x",1,0,reinterpret_cast<sockaddr *>(&address),sizeof(address)));
  } else {
    sockaddr_in6 address{}; address.sin6_family=AF_INET6; address.sin6_port=htons(9); address.sin6_addr=in6addr_loopback;
    result=connect(fd,reinterpret_cast<sockaddr *>(&address),sizeof(address));
  }
  int error=errno; close(fd); CHECK(result==-1 && (error==EPERM || error==EACCES));
}
static std::string hex(const std::string &s) {
  static const char digits[]="0123456789abcdef"; std::string result;
  for(unsigned char c:s) { result+=digits[c>>4]; result+=digits[c&15]; }
  return result;
}
static void generation(int fd,int id,const char *prompt) {
  auto h=handle(); CHECK(eilo_llm_load(h.get(),fd,2)==0);
  for(size_t i=0;i<ggml_backend_dev_count();++i) CHECK(ggml_backend_dev_type(ggml_backend_dev_get(i))==GGML_BACKEND_DEVICE_TYPE_CPU);
  CHECK(ggml_backend_dev_count()>0);
  CHECK(eilo_llm_begin(h.get(),prompt,static_cast<int32_t>(std::strlen(prompt)),8)==0);
  std::string text; int tokens=0, bytes=0; char out[1024];
  for(;;) {
    int result=eilo_llm_next(h.get(),out,sizeof(out),&bytes);
    if(result==0) { CHECK(bytes==0); break; }
    CHECK(result==1 && bytes>=0 && bytes<=1024); text.append(out,bytes); ++tokens;
    std::memset(out,0,sizeof(out)); CHECK(tokens<=8);
  }
  CHECK(tokens>0 && !text.empty()); CHECK(eilo_llm_next(h.get(),out,sizeof(out),&bytes)==0 && bytes==0);
  CHECK(eilo_llm_begin(h.get(),prompt,static_cast<int32_t>(std::strlen(prompt)),8)==-1);
  std::cout<<"GEN\t"<<id<<"\t"<<tokens<<"\t"<<hex(text)<<"\n";
}
int main(int argc,char **argv) {
  CHECK(argc==3); int fd=std::stoi(argv[1]), corrupt=std::stoi(argv[2]);
  network_probe(AF_INET,SOCK_STREAM); network_probe(AF_INET6,SOCK_STREAM); network_probe(AF_INET,SOCK_DGRAM);
  CHECK(fork()==-1 && (errno==EPERM || errno==EACCES));
  std::cout<<"NETWORK\tIPv4_TCP,IPv6_TCP,IPv4_UDP,process_fork\tDENIED\n";
  { auto h=handle(); CHECK(eilo_llm_load(h.get(),-1,2)==-1); }
  { auto h=handle(); CHECK(eilo_llm_load(h.get(),corrupt,2)==-3); }
  { auto h=handle(); eilo_llm_cancel(h.get()); CHECK(eilo_llm_load(h.get(),fd,2)==-2); }
  generation(fd,1,"The opposite of cold is");
  generation(fd,2,"One, two, three,");
  generation(fd,3,"The sky on a clear day is");
  { auto h=handle(); CHECK(eilo_llm_load(h.get(),fd,2)==0);
    CHECK(eilo_llm_begin(h.get(),"A short list of colors:",23,8)==0);
    char out[1024]; int bytes=0; CHECK(eilo_llm_next(h.get(),out,sizeof(out),&bytes)==1);
    std::memset(out,0,sizeof(out)); eilo_llm_cancel(h.get());
    CHECK(eilo_llm_next(h.get(),out,sizeof(out),&bytes)==-2 && bytes==0);
    for(char c:out) CHECK(c==0);
  }
  { auto h=handle(); CHECK(eilo_llm_load(h.get(),fd,2)==0);
    std::string prompt; for(int i=0;i<1800;++i) prompt+=" a";
    std::atomic<bool> entered{false}; int result=0;
    std::thread worker([&] { entered.store(true); result=eilo_llm_begin(h.get(),prompt.data(),static_cast<int32_t>(prompt.size()),8); });
    while(!entered.load()) std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(10)); eilo_llm_cancel(h.get()); worker.join(); CHECK(result==-2);
    char out[1024]; int bytes=0; CHECK(eilo_llm_next(h.get(),out,sizeof(out),&bytes)==-2 && bytes==0);
  }
  { auto h=handle(); std::atomic<bool> entered{false}; int result=0;
    std::thread worker([&] { entered.store(true); result=eilo_llm_load(h.get(),fd,2); });
    while(!entered.load()) std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(10)); eilo_llm_cancel(h.get()); worker.join(); CHECK(result==-2);
  }
  std::cout<<"LIFECYCLE\tinvalid_descriptor,corrupt_model,pre_cancel,post_token_cancel,concurrent_begin_cancel,concurrent_load_cancel\tPASS\n";
}
