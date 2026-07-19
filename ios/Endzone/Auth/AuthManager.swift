import AuthenticationServices
import Observation

@Observable
final class AuthManager {
    var userId: String?
    // The JWT sent as `Authorization: Bearer <identityToken>` on every
    // EndzoneAPI call — the backend's API Gateway JWT authorizer
    // verifies it against Apple's public JWKS (see backend/template.yaml
    // EndzoneHttpApi). Short-lived (Apple expires these after ~10 min);
    // this app doesn't refresh it mid-session, just re-captures a fresh
    // one on the next sign-in. Fine for a portfolio demo, not for a real
    // production session.
    var identityToken: String?

    var isSignedIn: Bool { userId != nil }

    func handle(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
                return
            }
            userId = credential.user
            identityToken = credential.identityToken.flatMap { String(data: $0, encoding: .utf8) }
        case .failure(let error):
            print("Sign in with Apple failed: \(error)")
            // TODO: surface to UI instead of just logging.
        }
    }

    #if DEBUG
    // Real Sign in with Apple is unreliable in Simulator (needs a signed-in
    // Apple ID, can hang on 2FA). This skips it for demoing the rest of the
    // app against FakeEndzoneAPI, which never checks the token's contents.
    func signInAsDemoUser() {
        userId = "demo-user"
        identityToken = "demo-token"
    }
    #endif
}
