import Foundation

/// Fixed-fixture lab review only, delivered as UILabel plain text after full validation.
/// Math comparisons remain readable; reasoning/role/tool or other tag markup fails closed.
enum TrialModelQualityText {
  static func decode(_ bytes:[UInt8])throws->String{
    guard (1...16384).contains(bytes.count),let text=String(bytes:bytes,encoding:.utf8),
      !text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,
      !text.unicodeScalars.contains(where:{$0.properties.generalCategory == .control && $0.value != 9 && $0.value != 10 && $0.value != 13}),
      text.range(of:"<[A-Za-z/!|]",options:.regularExpression)==nil else{throw QualityTextFailure.invalid}
    return text
  }
  enum QualityTextFailure:Error{case invalid}
}
