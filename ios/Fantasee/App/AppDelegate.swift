import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {
    var pushManager: PushNotificationManager?

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        pushManager?.didRegister(withDeviceToken: deviceToken)
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        pushManager?.didFailToRegister(error)
    }
}
