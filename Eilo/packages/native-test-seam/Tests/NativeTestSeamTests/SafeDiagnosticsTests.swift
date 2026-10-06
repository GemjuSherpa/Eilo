import XCTest
@testable import NativeTestSeam
final class SafeDiagnosticsTests: XCTestCase {
  func testBoundedVolatileCodesHaveNoContentFields() {
    let diagnostics = SafeDiagnostics()
    for _ in 0..<100 { diagnostics.record(.model, .unexpected, .error) }
    XCTAssertEqual(diagnostics.snapshot().count, 32)
    XCTAssertEqual(Set(Mirror(reflecting: diagnostics.snapshot()[0]).children.compactMap(\.label)), Set(["component", "code", "severity"]))
    diagnostics.clear()
    XCTAssertTrue(diagnostics.snapshot().isEmpty)
    XCTAssertTrue(SafeDiagnostics().snapshot().isEmpty)
  }
}
