import Foundation
public enum HistoryChoice:String,Codable { case unselected="none",privateMode="private",history }
public struct DisplayPreferences:Codable {
 public var text=true;public var images=false;public var video=false;public var voiceOnly=false
 public init() {}
}
public struct ConsentRecord:Codable {
 public var version=2;public var display:DisplayPreferences?=DisplayPreferences();public var historyChoice:HistoryChoice = .unselected;public var disclosureVersion=0;public var backgroundConsent=false;public var volume=100
 public init() {}
}
public protocol ConsentPersistence { func load() throws -> ConsentRecord?;func save(_ record:ConsentRecord) throws -> Bool }
/// Consent metadata is independent of microphone permission and protected-history capability.
public final class NativeConsentPolicy:@unchecked Sendable {
 private let lock=NSRecursiveLock();private let persistence:any ConsentPersistence;private let historyAvailable:()->Bool
 private var record=ConsentRecord();private var privateMode=true;private var privateExplicit=false
 public init(persistence:any ConsentPersistence,historyAvailable:@escaping ()->Bool={false}) {
  self.persistence=persistence;self.historyAvailable=historyAvailable
  if let loaded=try? persistence.load(),(1...2).contains(loaded.version),(0...1).contains(loaded.disclosureVersion),(0...100).contains(loaded.volume) { record=loaded;record.version=2;if record.display == nil { record.display=DisplayPreferences() } }
 }
 private func save(_ value:ConsentRecord)->Bool {
  do { guard try persistence.save(value) else { return false };record=value;return true } catch { return false }
 }
 @discardableResult public func chooseHistory(_ choice:HistoryChoice)->Bool {
  lock.lock();defer { lock.unlock() };guard choice != .unselected else { return false }
  var next=record;next.historyChoice=choice;guard save(next) else { return false }
  privateMode=true;privateExplicit=choice == .privateMode;return true
 }
 @discardableResult public func completeOnboarding()->Bool {
  lock.lock();defer { lock.unlock() };guard record.historyChoice != .unselected else { return false }
  var next=record;next.disclosureVersion=1;return save(next)
 }
 public var canStart:Bool { lock.lock();defer { lock.unlock() };return record.disclosureVersion==1 && record.historyChoice != .unselected && (record.historyChoice == .privateMode || privateExplicit || (historyAvailable() && !privateMode)) }
 @discardableResult public func choosePrivateSession(_ enabled:Bool)->Bool {
  lock.lock();defer { lock.unlock() };guard enabled else { return false }
  privateMode=true;privateExplicit=true;return true
 }
 @discardableResult public func chooseVolume(_ volume:Int)->Bool {
  lock.lock();defer { lock.unlock() };guard (0...100).contains(volume) else { return false }
  var next=record;next.volume=volume;return save(next)
 }
 @discardableResult public func chooseBackground(_ enabled:Bool,authenticated:Bool)->Bool {
  lock.lock();defer { lock.unlock() }
  guard !enabled || (authenticated && record.disclosureVersion==1 && record.historyChoice != .unselected) else { return false }
  var next=record;next.backgroundConsent=enabled;return save(next)
 }
 public var backgroundRequested:Bool { lock.lock();defer { lock.unlock() };return record.backgroundConsent && record.disclosureVersion==1 && record.historyChoice != .unselected }
 public var personalWritesAllowed:Bool { lock.lock();defer { lock.unlock() };return record.historyChoice == .history && !privateMode && historyAvailable() }
 /// UI-only preference changes require a foreground, unlocked native host. No voice-command route is exposed.
 @discardableResult public func chooseDisplay(_ name:String,enabled:Bool,authorized:Bool)->Bool {
  lock.lock();defer { lock.unlock() };guard authorized else { return false }
  var next=record;var display=next.display ?? DisplayPreferences()
  switch name { case "displayText":display.text=enabled;case "displayImages":display.images=enabled;case "displayVideo":display.video=enabled;case "voiceOnly":display.voiceOnly=enabled;default:return false }
  next.display=display;return save(next)
 }
 public func snapshot()->[String:Any] {
  lock.lock();defer { lock.unlock() }
  let d=record.display ?? DisplayPreferences()
  return ["version":2,"display":["text":d.text,"images":d.images,"video":d.video,"voiceOnly":d.voiceOnly],"historyChoice":record.historyChoice.rawValue,"onboardingComplete":record.disclosureVersion==1 && record.historyChoice != .unselected,"historyAvailable":historyAvailable(),"historyEnabled":personalWritesAllowed,"backgroundConsent":record.backgroundConsent,"privateSession":privateMode,"volume":record.volume]
 }
}
#if os(iOS)
public final class IOSConsentPersistence:ConsentPersistence {
 private let root:URL? = FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask).first?.appendingPathComponent("local-consent",isDirectory:true)
 public init() {}
 public func load() throws -> ConsentRecord? {
  guard let root else { return nil };let file=root.appendingPathComponent("choices.json")
  guard FileManager.default.fileExists(atPath:file.path) else { return nil }
  let attributes=try FileManager.default.attributesOfItem(atPath:file.path)
  guard let size=attributes[.size] as? NSNumber,size.intValue<=4096 else { return nil }
  let data=try Data(contentsOf:file)
  guard let object=try JSONSerialization.jsonObject(with:data) as? [String:Any],let version=object["version"] as? Int else { return nil }
  let legacy:Set<String>=["version","historyChoice","disclosureVersion","backgroundConsent","volume"]
  guard (version==1 && Set(object.keys)==legacy) || (version==2 && Set(object.keys)==legacy.union(["display"])) else { return nil }
  if version==2 { guard let display=object["display"] as? [String:Any],Set(display.keys)==Set(["text","images","video","voiceOnly"]) else { return nil } }
  return try JSONDecoder().decode(ConsentRecord.self,from:data)
 }
 public func save(_ record:ConsentRecord) throws -> Bool {
  guard var root else { return false }
  try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true,attributes:[.protectionKey:FileProtectionType.complete])
  var values=URLResourceValues();values.isExcludedFromBackup=true;try root.setResourceValues(values)
  try JSONEncoder().encode(record).write(to:root.appendingPathComponent("choices.json"),options:[.atomic,.completeFileProtection]);return true
 }
}
#endif
