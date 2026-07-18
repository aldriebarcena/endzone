import Foundation

// Lets the UI be built and run now, ahead of the backend API surface
// existing at all (DESIGN.md: "can be stubbed against fake data earlier
// to parallelize"). Data below mirrors the real scoring play captured in
// backend/tests/fixtures/tank01_box_score_final.json (Phase 2).
final class FakeFantaseeAPI: FantaseeAPI {
    func fetchLiveGame(gameId: String) async throws -> GameStateDTO {
        GameStateDTO(
            gameId: gameId,
            status: "In Progress",
            homeTeam: "BUF",
            awayTeam: "NYJ",
            homeScore: 21,
            awayScore: 8,
            period: "Q3",
            clock: "7:46",
            events: [
                ScoringEventDTO(
                    eventId: "\(gameId):Q1:8:17:BUF:TD",
                    gameId: gameId,
                    team: "BUF",
                    scoringType: "TD",
                    description: "Dawson Knox 17 Yd pass from Mitchell Trubisky (Matt Prater Kick)",
                    period: "Q1",
                    gameClock: "8:17",
                    homeScore: 7,
                    awayScore: 0,
                    playerIds: ["3039707", "3930086", "11122"]
                ),
                ScoringEventDTO(
                    eventId: "\(gameId):Q2:11:43:BUF:TD",
                    gameId: gameId,
                    team: "BUF",
                    scoringType: "TD",
                    description: "Ty Johnson 6 Yd Rush (Matt Prater Kick)",
                    period: "Q2",
                    gameClock: "11:43",
                    homeScore: 14,
                    awayScore: 0,
                    playerIds: ["3915411", "11122"]
                )
            ],
            fetchedAt: Date()
        )
    }

    func importLeague(leagueId: String, authToken: String) async throws -> LeagueConfigDTO {
        LeagueConfigDTO(
            userId: "fake-user",
            sleeperLeagueId: leagueId,
            leagueName: "Fake League",
            season: "2026",
            pointValues: ["pass_td": 6.0, "rush_td": 6.0, "rec": 1.0, "rec_td": 6.0],
            importedAt: Date()
        )
    }

    func registerDeviceToken(_ deviceToken: String, authToken: String) async throws {
        // No-op — nothing to persist against in the fake implementation.
    }
}
