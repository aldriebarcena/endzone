# ios/

Swift/SwiftUI client — see [DESIGN.md](../DESIGN.md#ios-client).

Generated via [XcodeGen](https://github.com/yonaskolb/XcodeGen) from `project.yml` — `Endzone.xcodeproj` and `Generated/` are committed so the project opens directly in Xcode without needing XcodeGen installed. If you change `project.yml`, regenerate with:

```
xcodegen generate
```

Currently runs against `FakeEndzoneAPI` (stubbed data) since the backend has no public API surface yet (see [PROJECT_PLAN.md](../PROJECT_PLAN.md)'s open questions). `PRODUCT_BUNDLE_IDENTIFIER` is a placeholder (`com.endzone.app`) pending a real Apple Developer Team.

## Running it

```
open Endzone.xcodeproj
```

Or from the CLI:
```
xcodebuild -project Endzone.xcodeproj -scheme Endzone -destination 'platform=iOS Simulator,name=iPhone 17' build
```
