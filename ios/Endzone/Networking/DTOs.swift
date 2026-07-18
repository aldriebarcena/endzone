import Foundation

// Wire format for backend/template.yaml's EndzoneHttpApi (not deployed —
// see PROJECT_PLAN.md's scope decision). Kept separate from the SwiftData
// @Model types, same as the backend keeps GameState/ScoringEvent separate
// from DynamoDB item shape (storage.py).

struct GameStateDTO: Codable {
    let gameId: String
    let status: String
    let statusCode: Int
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
    // player_id -> fantasy points earned from this play, personalized
    // for whichever user made the request (backend/src/api/get_live_game
    // computes this against the caller's own LeagueConfig.pointValues).
    // Empty when the play type isn't scored yet (fantasy_points.py's
    // PLAY_TYPE_ROLES) or the user hasn't imported a league.
    let points: [String: Double]
    let playerNames: [String: String]
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

struct RegisterDeviceTokenRequest: Codable {
    let deviceToken: String
}
