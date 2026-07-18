import SwiftData
import SwiftUI

@main
struct FantaseeApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var authManager = AuthManager()
    @State private var pushManager = PushNotificationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(authManager)
                .environment(pushManager)
                .task {
                    appDelegate.pushManager = pushManager
                    await pushManager.requestAuthorization()
                }
        }
        .modelContainer(for: [GameState.self, ScoringEvent.self, LeagueConfig.self])
    }
}
