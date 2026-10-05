// swift-tools-version: 5.9
import PackageDescription
let package = Package(
  name: "NativeTestSeam",
  products: [.library(name: "NativeTestSeam", targets: ["NativeTestSeam"])],
  targets: [.target(name: "NativeTestSeam"), .testTarget(name: "NativeTestSeamTests", dependencies: ["NativeTestSeam"])]
)
