import Foundation
import SwiftUI

protocol FantaseeAPI {
    func fetchLiveGame(gameId: String) async throws -> GameStateDTO
    // authToken is the caller's current Sign in with Apple identity token
    // (AuthManager.identityToken) — the client stays stateless about auth
    // itself; whoever calls these supplies the token they currently have.
    func importLeague(leagueId: String, authToken: String) async throws -> LeagueConfigDTO
    func registerDeviceToken(_ deviceToken: String, authToken: String) async throws
}

enum APIError: Error {
    case badResponse(statusCode: Int)
}

// A single shared instance, injected once in FantaseeApp — lets
// AuthManager/PushNotificationManager coordination code and every view
// reach the same client without each owning its own, and swapping
// FakeFantaseeAPI for URLSessionFantaseeAPI later is a one-line change
// at the injection point.
private struct FantaseeAPIKey: EnvironmentKey {
    static let defaultValue: FantaseeAPI = FakeFantaseeAPI()
}

extension EnvironmentValues {
    var fantaseeAPI: FantaseeAPI {
        get { self[FantaseeAPIKey.self] }
        set { self[FantaseeAPIKey.self] = newValue }
    }
}
