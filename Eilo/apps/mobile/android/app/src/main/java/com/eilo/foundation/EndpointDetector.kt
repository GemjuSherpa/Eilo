package com.eilo.foundation
internal enum class EndpointResult { CONTINUE, COMPLETE, NO_SPEECH, LIMIT, INVALID }
/** Sample-clocked 16 kHz VAD policy; probabilities must come from a separately verified native VAD.
 * Eight consecutive high-confidence 20 ms frames confirm speech; 500 ms silence ends a turn.
 * Unknown/overlap is not silence. Empty/noise cannot manufacture a speech endpoint.
 */
internal class EndpointDetector {
 private var total=0;private var high=0;private var quiet=0;private var speech=false;private var terminal=false
 fun advance(probability:Float,samples:Int=320):EndpointResult {
  if(terminal)return EndpointResult.INVALID
  if(samples!=320 || !probability.isFinite() || probability !in 0f..1f){terminal=true;return EndpointResult.INVALID}
  total+=samples
  when {
   probability>=.8f->{high+=samples;quiet=0;if(high>=2560)speech=true}
   probability<=.2f->{high=0;if(speech)quiet+=samples}
   else->{high=0;quiet=0}
  }
  val result=when {
   speech && quiet>=8000->EndpointResult.COMPLETE
   !speech && total>=80000->EndpointResult.NO_SPEECH
   total>=480000->EndpointResult.LIMIT
   else->EndpointResult.CONTINUE
  }
  terminal=result!=EndpointResult.CONTINUE;return result
 }
 fun confirmedSpeech()=speech
 fun elapsedSamples()=total
}
