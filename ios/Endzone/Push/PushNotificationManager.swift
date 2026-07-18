import Observation
import UIKit
import UserNotifications

@Observable
final class PushNotificationManager {
    var deviceToken: String?

    func requestAuthorization() async {
        do {
            let granted = try await UNUserNotificationCenter.current()
                .requestAuthorization(options: [.alert, .sound, .badge])
            if granted {
                await MainActor.run {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        } catch {
            print("push authorization request failed: \(error)")
        }
    }

    func didRegister(withDeviceToken tokenData: Data) {
        deviceToken = tokenData.map { String(format: "%02x", $0) }.joined()
        // TODO: send to backend once the LeagueConfig write API exists —
        // see PROJECT_PLAN.md open questions. Can't verify end-to-end
        // delivery at all yet regardless: that needs a real Apple
        // Developer Team + APNs auth key, which isn't set up (same gap
        // flagged for the backend's APNs sandbox testing in Phase 4).
    }

    func didFailToRegister(_ error: Error) {
        print("failed to register for remote notifications: \(error)")
    }
}
