import Foundation

// The real backend implementation. Matches backend/template.yaml's
// FantaseeHttpApi routes (POST /leagues, PUT /device-token) and the
// Sign in with Apple JWT auth its authorizer expects. Untestable
// end-to-end right now regardless — the API isn't deployed (see
// PROJECT_PLAN.md's scope decision), so this is verified by matching
// the backend's actual route/handler code, not by hitting a live
// endpoint.
final class URLSessionFantaseeAPI: FantaseeAPI {
    private let baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session

        // No key conversion strategy: the backend's DynamoDB items
        // (storage.py, league_import.py) already use camelCase — matches
        // Swift's convention directly, no translation needed. The actual
        // API Gateway response format is still TBD (doesn't exist yet),
        // but this is the natural choice for consistency with the rest
        // of the backend's wire formats.
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        self.decoder = decoder

        let encoder = JSONEncoder()
        self.encoder = encoder
    }

    func fetchLiveGame(gameId: String) async throws -> GameStateDTO {
        let url = baseURL.appendingPathComponent("games").appendingPathComponent(gameId)
        let (data, response) = try await session.data(from: url)
        try Self.validate(response)
        return try decoder.decode(GameStateDTO.self, from: data)
    }

    func importLeague(leagueId: String, authToken: String) async throws -> LeagueConfigDTO {
        var request = URLRequest(url: baseURL.appendingPathComponent("leagues"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try encoder.encode(ImportLeagueRequest(sleeperLeagueId: leagueId))

        let (data, response) = try await session.data(for: request)
        try Self.validate(response)
        return try decoder.decode(LeagueConfigDTO.self, from: data)
    }

    func registerDeviceToken(_ deviceToken: String, authToken: String) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("device-token"))
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        request.httpBody = try encoder.encode(RegisterDeviceTokenRequest(deviceToken: deviceToken))

        let (_, response) = try await session.data(for: request)
        try Self.validate(response)
    }

    private static func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
            throw APIError.badResponse(statusCode: statusCode)
        }
    }
}
