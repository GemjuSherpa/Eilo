import Foundation

enum QwenRole:String{case user,assistant}
struct QwenTurn{let role:QwenRole,text:String}
enum QwenPromptFailure:Error{case unavailable}
/// Restricted no-tools subset of pinned Qwen3, hard enable_thinking=false.
/// Fixed native rules are the only system content; arbitrary role strings are absent.
enum QwenTemplate {
  static let rules=PersonaPolicy.rules+CapabilityPolicy.rules
  static let suffix="<|im_start|>assistant\n<think>\n\n</think>\n\n"
  static func data(_ text:String)throws->String{guard !text.contains("\0"),text.utf8.count<=16384 else{throw QwenPromptFailure.unavailable};return text.replacingOccurrences(of:"<",with:"＜").replacingOccurrences(of:">",with:"＞")}
  static func render(latest:String,history:[QwenTurn]=[])throws->String{
    guard !latest.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,history.count<=32 else{throw QwenPromptFailure.unavailable}
    var text="<|im_start|>system\n"+rules+"<|im_end|>\n"
    for turn in history{text += "<|im_start|>"+turn.role.rawValue+"\n"+(try data(turn.text))+"<|im_end|>\n"}
    text += "<|im_start|>user\n"+(try data(latest))+"<|im_end|>\n"+suffix
    guard text.utf8.count<=16384 else{throw QwenPromptFailure.unavailable};return text
  }
}
/// Worker-confined UTF-8 guard. Any angle markup (split reasoning/role/tool tags),
/// malformed UTF-8, NUL, stale lease or oversized output fails closed. Emitted text
/// is not speech-authorized; S07 still checks every fragment. Caller cancels on Stop.
final class NonThinkingOutput {
  private let current:()->Bool,emit:(String)throws->Void
  private var pending:[UInt8]=[],total=0,closed=false
  init(current:@escaping()->Bool={false},emit:@escaping(String)throws->Void){self.current=current;self.emit=emit}
  func append(_ piece:UnsafeBufferPointer<UInt8>)throws{
    do {
      guard !closed,current(),(1...1024).contains(piece.count),total+piece.count<=16384 else{throw QwenPromptFailure.unavailable}
      total+=piece.count;var bytes=pending+Array(piece);pending.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};pending=[]
      defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
      var i=0
      while i<bytes.count{
        let lead=bytes[i];guard lead != 0,lead != 60,lead != 62 else{throw QwenPromptFailure.unavailable}
        let width:Int
        switch lead{case 1...127:width=1;case 194...223:width=2;case 224...239:width=3;case 240...244:width=4;default:throw QwenPromptFailure.unavailable}
        if i+width>bytes.count{pending=Array(bytes[i...]);break}
        guard String(bytes:bytes[i..<i+width],encoding:.utf8) != nil else{throw QwenPromptFailure.unavailable};i+=width
      }
      if i>0{guard current(),let text=String(bytes:bytes[..<i],encoding:.utf8) else{throw QwenPromptFailure.unavailable};try emit(text);guard current() else{throw QwenPromptFailure.unavailable}}
    }catch{cancel();throw QwenPromptFailure.unavailable}
  }
  func finish()throws{guard !closed,current(),pending.isEmpty else{cancel();throw QwenPromptFailure.unavailable};closed=true}
  func cancel(){closed=true;pending.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};pending=[]}
  deinit{cancel()}
}
