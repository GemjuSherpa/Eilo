import Foundation
@main struct QualityStateProbe {
  static func require(_ value:Bool){if !value{fatalError("Model quality state invariant failed")}}
  static func main(){
    let s=TrialModelQualitySession();require(s.nextFixture==1 && !s.awaitingRating && !s.rate(5))
    let (a,f)=s.begin()!;require(f==1 && s.begin()==nil && !s.rate(5) && !s.finish(UUID()))
    require(s.finish(a) && !s.finish(a) && s.awaitingRating && !s.rate(0) && !s.rate(6))
    s.cancel();require(!s.awaitingRating && !s.rate(5) && !s.finish(a) && s.nextFixture==1)
    let (b,_)=s.begin()!;require(!s.finish(a) && s.fail(b) && !s.fail(b) && !s.rate(5))
    let (c,_)=s.begin()!;require(s.finish(c) && s.rate(4) && !s.rate(5) && s.nextFixture==2)
    for fixture in 2...6{let (ticket,actual)=s.begin()!;require(actual==fixture && s.finish(ticket) && s.rate(3))}
    require(s.nextFixture==nil && s.begin()==nil && s.aggregate.count==8)
    let stopped=TrialModelQualitySession()
    for _ in 0..<3{let (ticket,_)=stopped.begin()!;stopped.cancel();require(!stopped.finish(ticket) && !stopped.rate(5))}
    require(stopped.begin()==nil && stopped.nextFixture==1)
    print("Model quality stale/cancel/retry/rating/order state probe PASS")
  }
}
