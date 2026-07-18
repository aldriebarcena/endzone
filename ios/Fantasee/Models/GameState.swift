import Foundation
import SwiftData

// Mirrors backend/src/models.py GameState.
@Model
final class GameState {
    @Attribute(.unique) var gameId: String
    var status: String
    var homeTeam: String
    var awayTeam: String
    var homeScore: Int
    var awayScore: Int
    var period: String
    var clock: String?
    var fetchedAt: Date

    @Relationship(deleteRule: .cascade) var events: [ScoringEvent]

    init(
        gameId: String,
        status: String,
        homeTeam: String,
        awayTeam: String,
        homeScore: Int,
        awayScore: Int,
        period: String,
        clock: String?,
        events: [ScoringEvent] = [],
        fetchedAt: Date
    ) {
        self.gameId = gameId
        self.status = status
        self.homeTeam = homeTeam
        self.awayTeam = awayTeam
        self.homeScore = homeScore
        self.awayScore = awayScore
        self.period = period
        self.clock = clock
        self.events = events
        self.fetchedAt = fetchedAt
    }
}
