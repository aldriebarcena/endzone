import Foundation

// The real backend implementation. Untestable end-to-end right now — the
// backend API surface this talks to doesn't exist yet (see
// PROJECT_PLAN.md's "no API surface for the iOS client" open question).
// Written against the shape that API will need to have, not verified
// against a live endpoint.
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

    func importLeague(leagueId: String) async throws -> LeagueConfigDTO {
        var request = URLRequest(url: baseURL.appendingPathComponent("league-config"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(ImportLeagueRequest(sleeperLeagueId: leagueId))

        let (data, response) = try await session.data(for: request)
        try Self.validate(response)
        return try decoder.decode(LeagueConfigDTO.self, from: data)
    }

    private static func validate(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            let statusCode = (response as? HTTPURLResponse)?.statusCode ?? -1
            throw APIError.badResponse(statusCode: statusCode)
        }
    }
}
