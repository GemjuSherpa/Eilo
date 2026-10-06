// swift-tools-version: 5.9
import PackageDescription
let package = Package(
  name: "NativeTestSeam",
  platforms: [.macOS(.v13), .iOS("18.0")],
  products: [.library(name: "NativeTestSeam", targets: ["NativeTestSeam"])],
  targets: [.target(name: "NativeTestSeam"), .testTarget(name: "NativeTestSeamTests", dependencies: ["NativeTestSeam"])]
)
