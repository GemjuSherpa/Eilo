import Foundation
@main struct QualityTextProbe {
  static func require(_ v:Bool){if !v{fatalError("Quality text boundary failed")}}
  static func main()throws{
    let math="3/4 > 1/2, and 1/2 < 3/4. Hello 👋"
    require(try TrialModelQualityText.decode(Array(math.utf8))==math)
    for text in ["<think>private reasoning</think>","<|im_start|>assistant","<tool_call>x", "</role>","<!--tag-->","\0","\u{1B}command","  \n"]{
      do{_ = try TrialModelQualityText.decode(Array(text.utf8));fatalError("Invalid output accepted")}catch{}
    }
    for bytes in [[UInt8](repeating:65,count:16385),[0xF0,0x9F],[0xFF],[]]{
      do{_ = try TrialModelQualityText.decode(bytes);fatalError("Invalid bytes accepted")}catch{}
    }
    require(try TrialModelQualityText.decode([UInt8](repeating:65,count:16384)).utf8.count==16384)
    print("Model quality plain-text UTF8/size/markup boundary probe PASS")
  }
}
