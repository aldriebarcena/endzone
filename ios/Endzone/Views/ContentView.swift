import SwiftUI

struct ContentView: View {
    @Environment(AuthManager.self) private var authManager

    var body: some View {
        if authManager.isSignedIn {
            LiveFeedView()
        } else {
            SignInView()
        }
    }
}

#Preview {
    ContentView()
        .environment(AuthManager())
        .environment(PushNotificationManager())
}
