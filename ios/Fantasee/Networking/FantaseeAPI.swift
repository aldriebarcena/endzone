import Foundation

protocol FantaseeAPI {
    func fetchLiveGame(gameId: String) async throws -> GameStateDTO
    func importLeague(leagueId: String) async throws -> LeagueConfigDTO
}

enum APIError: Error {
    case badResponse(statusCode: Int)
}
