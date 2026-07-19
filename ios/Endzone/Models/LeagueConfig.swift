import Foundation
import SwiftData

// Mirrors the LeagueConfig DynamoDB item shape written by
// backend/src/league_import.py. deviceToken is written via PUT
// /device-token (backend/src/api/register_device_token); pointValues has
// no override API yet and stays seeded read-only from Sleeper.
@Model
final class LeagueConfig {
    @Attribute(.unique) var userId: String
    var sleeperLeagueId: String
    var leagueName: String
    var season: String
    var pointValues: [String: Double]
    var importedAt: Date
    var deviceToken: String?

    init(
        userId: String,
        sleeperLeagueId: String,
        leagueName: String,
        season: String,
        pointValues: [String: Double],
        importedAt: Date,
        deviceToken: String? = nil
    ) {
        self.userId = userId
        self.sleeperLeagueId = sleeperLeagueId
        self.leagueName = leagueName
        self.season = season
        self.pointValues = pointValues
        self.importedAt = importedAt
        self.deviceToken = deviceToken
    }
}
