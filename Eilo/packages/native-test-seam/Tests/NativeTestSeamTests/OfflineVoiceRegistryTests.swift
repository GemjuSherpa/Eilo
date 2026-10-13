import XCTest
@testable import NativeTestSeam
final class OfflineVoiceRegistryTests:XCTestCase {
  struct Ready:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
  func voice(_ id:String="en-au",installed:Bool=true,network:Bool?=false,verified:Bool=false)->OfflineVoice{OfflineVoice(id:id,language:"en-AU",installed:installed,networkRequired:network,offlineVerified:verified)}
  func testMissingNetworkUnknownAndUninstalledGateSetup(){
    let r=OfflineVoiceRegistry(),gate=VoiceAwareReadiness(models:Ready(),voices:OfflineVoiceRegistry())
    XCTAssertEqual(gate.status(),.offlineVoiceMissing)
    for values in [[],[voice(network:true)],[voice(installed:false)],[voice(network:nil)]]{XCTAssertFalse(r.refresh(values));XCTAssertNil(r.selection())}
    XCTAssertTrue(r.refresh([voice()]));XCTAssertEqual(VoiceAwareReadiness(models:Ready(),voices:r).status(),.ready)
    XCTAssertEqual(VoiceAwareReadiness(models:MissingModelReadiness(),voices:r).status(),.missing)
  }
  func testExactSelectionAndRefreshRevocation(){let r=OfflineVoiceRegistry();XCTAssertTrue(r.refresh([voice("en-us"),voice()],requested:"en-au"));let old=r.selection()!;XCTAssertTrue(r.current(old));XCTAssertFalse(r.refresh([voice("en-us")],requested:"en-au"));XCTAssertFalse(r.current(old));r.invalidate();XCTAssertFalse(r.ready)}
  func testUnknownNeedsEvidenceAndNetworkCannotOverride(){let r=OfflineVoiceRegistry();XCTAssertTrue(r.refresh([voice(network:nil,verified:true)]));XCTAssertFalse(r.refresh([voice(network:true,verified:true)]))}
  func testDuplicateInvalidAndOversizeSnapshots(){let r=OfflineVoiceRegistry();XCTAssertFalse(r.refresh([voice(),voice()]));XCTAssertFalse(r.refresh([voice("invalid/voice")]));XCTAssertFalse(r.refresh((0..<129).map{voice("v-\($0)")}))}
}
