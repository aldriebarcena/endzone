import Foundation
import SwiftData

// Mirrors backend/src/models.py ScoringEvent. `description` is avoided as
// a property name — it collides with CustomStringConvertible/NSObject.
@Model
final class ScoringEvent {
    @Attribute(.unique) var eventId: String
    var gameId: String
    var team: String
    var scoringType: String
    var eventDescription: String
    var period: String
    var gameClock: String
    var homeScore: Int
    var awayScore: Int
    var playerIds: [String]
    var fetchedAt: Date

    init(
        eventId: String,
        gameId: String,
        team: String,
        scoringType: String,
        eventDescription: String,
        period: String,
        gameClock: String,
        homeScore: Int,
        awayScore: Int,
        playerIds: [String],
        fetchedAt: Date
    ) {
        self.eventId = eventId
        self.gameId = gameId
        self.team = team
        self.scoringType = scoringType
        self.eventDescription = eventDescription
        self.period = period
        self.gameClock = gameClock
        self.homeScore = homeScore
        self.awayScore = awayScore
        self.playerIds = playerIds
        self.fetchedAt = fetchedAt
    }
}
