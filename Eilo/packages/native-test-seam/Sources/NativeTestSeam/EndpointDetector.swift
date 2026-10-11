import Foundation
enum EndpointResult {case continued,complete,noSpeech,limit,invalid}
/// Native verified VAD probabilities only; sample-clocked bounds are independent of wall scheduling.
final class EndpointDetector {
 private var total=0,high=0,quiet=0;private(set) var confirmedSpeech=false;private var terminal=false
 func advance(_ probability:Float,samples:Int=320)->EndpointResult {
  guard !terminal,samples==320,probability.isFinite,(0...1).contains(probability) else{terminal=true;return .invalid}
  total+=samples
  if probability>=0.8{high+=samples;quiet=0;if high>=2560{confirmedSpeech=true}}
  else if probability<=0.2{high=0;if confirmedSpeech{quiet+=samples}}
  else{high=0;quiet=0}
  let result:EndpointResult
  if confirmedSpeech && quiet>=8000{result = .complete}
  else if !confirmedSpeech && total>=80000{result = .noSpeech}
  else if total>=480000{result = .limit}
  else{result = .continued}
  terminal=result != .continued;return result
 }
 var elapsedSamples:Int{total}
}
