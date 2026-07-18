import Foundation

// Wire format for the (not-yet-built) backend API — see PROJECT_PLAN.md's
// "no API surface for the iOS client" open question. Kept separate from
// the SwiftData @Model types, same as the backend keeps GameState/
// ScoringEvent separate from DynamoDB item shape (storage.py).

struct GameStateDTO: Codable {
    let gameId: String
    let status: String
    let homeTeam: String
    let awayTeam: String
    let homeScore: Int
    let awayScore: Int
    let period: String
    let clock: String?
    let events: [ScoringEventDTO]
    let fetchedAt: Date
}

struct ScoringEventDTO: Codable {
    let eventId: String
    let gameId: String
    let team: String
    let scoringType: String
    let description: String
    let period: String
    let gameClock: String
    let homeScore: Int
    let awayScore: Int
    let playerIds: [String]
}

struct LeagueConfigDTO: Codable {
    let userId: String
    let sleeperLeagueId: String
    let leagueName: String
    let season: String
    let pointValues: [String: Double]
    let importedAt: Date
}

struct ImportLeagueRequest: Codable {
    let sleeperLeagueId: String
}
