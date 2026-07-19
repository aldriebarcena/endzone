import AuthenticationServices
import SwiftUI

struct SignInView: View {
    @Environment(AuthManager.self) private var authManager

    var body: some View {
        VStack(spacing: 16) {
            Text("Endzone")
                .font(.largeTitle.bold())
            Text("Live fantasy scoring, as it happens.")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            SignInWithAppleButton(.signIn) { request in
                request.requestedScopes = [.fullName, .email]
            } onCompletion: { result in
                authManager.handle(result)
            }
            .signInWithAppleButtonStyle(.black)
            .frame(height: 44)
            .padding(.horizontal, 40)
            .padding(.top, 24)

            #if DEBUG
            Button("Continue as Demo User") {
                authManager.signInAsDemoUser()
            }
            .padding(.top, 8)
            #endif
        }
        .padding()
    }
}

#Preview {
    SignInView()
        .environment(AuthManager())
}
