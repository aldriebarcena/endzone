import SwiftData
import SwiftUI

@main
struct EndzoneApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @State private var authManager = AuthManager()
    @State private var pushManager = PushNotificationManager()
    // TODO: swap for URLSessionEndzoneAPI() once the backend is actually
    // deployed (currently optional — see root README's scope decision).
    private let api: EndzoneAPI = FakeEndzoneAPI()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(authManager)
                .environment(pushManager)
                .environment(\.endzoneAPI, api)
                .task {
                    appDelegate.pushManager = pushManager
                    await pushManager.requestAuthorization()
                }
                .onChange(of: authManager.userId) { registerDeviceTokenIfReady() }
                .onChange(of: pushManager.deviceToken) { registerDeviceTokenIfReady() }
        }
        .modelContainer(for: [GameState.self, ScoringEvent.self, LeagueConfig.self])
    }

    // Fires once both halves exist: a signed-in user (with a fresh
    // identity token to authenticate the call) and a device token from
    // APNs registration. Order-independent — either one can arrive first.
    private func registerDeviceTokenIfReady() {
        guard let authToken = authManager.identityToken, let deviceToken = pushManager.deviceToken else {
            return
        }
        Task {
            do {
                try await api.registerDeviceToken(deviceToken, authToken: authToken)
            } catch {
                print("failed to register device token: \(error)")
            }
        }
    }
}
