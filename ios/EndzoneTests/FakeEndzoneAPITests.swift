import Testing
@testable import Endzone

struct FakeEndzoneAPITests {
    @Test func fetchLiveGameReturnsGameWithScoringPlays() async throws {
        let api = FakeEndzoneAPI()

        let game = try await api.fetchLiveGame(authToken: "fake-token")

        #expect(!game.events.isEmpty)
        #expect(game.events.allSatisfy { $0.gameId == game.gameId })
    }

    @Test func fetchLiveGameIncludesRealComputedFantasyPoints() async throws {
        // These are the real numbers verified in
        // backend/tests/test_fantasy_points.py, not placeholder values --
        // this is the whole point of the app.
        let api = FakeEndzoneAPI()

        let game = try await api.fetchLiveGame(authToken: "fake-token")

        let passingTD = try #require(game.events.first { $0.description.contains("Dawson Knox") })
        #expect(passingTD.points["3930086"] == 8.7)
        #expect(passingTD.playerNames["3930086"] == "Dawson Knox")
    }

    @Test func importLeagueReturnsSeededPointValues() async throws {
        let api = FakeEndzoneAPI()

        let config = try await api.importLeague(leagueId: "12345", authToken: "fake-token")

        #expect(config.sleeperLeagueId == "12345")
        #expect(config.pointValues["pass_td"] == 6.0)
    }

    @Test func registerDeviceTokenDoesNotThrow() async throws {
        let api = FakeEndzoneAPI()

        try await api.registerDeviceToken("abc123", authToken: "fake-token")
    }
}
