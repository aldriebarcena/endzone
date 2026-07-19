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
        // Actual registration happens in EndzoneApp.swift's
        // registerDeviceTokenIfReady() once both this token and a signed-
        // in user exist. Can't verify end-to-end delivery at all yet
        // regardless: that needs a real Apple Developer Team + APNs auth
        // key, which isn't set up.
    }

    func didFailToRegister(_ error: Error) {
        print("failed to register for remote notifications: \(error)")
    }
}
