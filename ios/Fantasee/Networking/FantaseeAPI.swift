import Foundation
import SwiftUI

protocol FantaseeAPI {
    // No gameId parameter -- matches backend/src/api/get_live_game, which
    // always returns whichever single game the backend is currently
    // tracking (DESIGN.md's v1 scope: one live game at a time, globally).
    // Requires authToken because the response is personalized: points
    // are computed against the caller's own LeagueConfig.pointValues.
    //
    // authToken is the caller's current Sign in with Apple identity token
    // (AuthManager.identityToken) — the client stays stateless about auth
    // itself; whoever calls these supplies the token they currently have.
    func fetchLiveGame(authToken: String) async throws -> GameStateDTO
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
