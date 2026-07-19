# ios/

Swift/SwiftUI client. Not currently running against real infrastructure — see the root [README](../README.md) for scope.

Generated via [XcodeGen](https://github.com/yonaskolb/XcodeGen) from `project.yml` — `Endzone.xcodeproj` and `Generated/` are committed so the project opens directly in Xcode without needing XcodeGen installed. If you change `project.yml`, regenerate with:

```
xcodegen generate
```

Currently runs against `FakeEndzoneAPI` (stubbed data) since the backend isn't deployed; swapping to `URLSessionEndzoneAPI` is a one-line change at the `EndzoneApp.swift` injection point once it is. `PRODUCT_BUNDLE_IDENTIFIER` is a placeholder (`com.endzone.app`) pending a real Apple Developer Team.

## Running it

```
open Endzone.xcodeproj
```

Or from the CLI:
```
xcodebuild -project Endzone.xcodeproj -scheme Endzone -destination 'platform=iOS Simulator,name=iPhone 17' build
```
