import AuthenticationServices
import Observation

@Observable
final class AuthManager {
    var userId: String?

    var isSignedIn: Bool { userId != nil }

    func handle(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential else {
                return
            }
            userId = credential.user
            // TODO: send credential.identityToken to the backend once the
            // LeagueConfig write API exists. Backend needs to verify this
            // JWT against Apple's public JWKS to trust `userId` — see
            // PROJECT_PLAN.md open questions.
        case .failure(let error):
            print("Sign in with Apple failed: \(error)")
            // TODO: surface to UI instead of just logging.
        }
    }
}
