import Testing
@testable import Fantasee

struct FakeFantaseeAPITests {
    @Test func fetchLiveGameReturnsGameWithScoringPlays() async throws {
        let api = FakeFantaseeAPI()

        let game = try await api.fetchLiveGame(gameId: "demo")

        #expect(game.gameId == "demo")
        #expect(!game.events.isEmpty)
        #expect(game.events.allSatisfy { $0.gameId == "demo" })
    }

    @Test func importLeagueReturnsSeededPointValues() async throws {
        let api = FakeFantaseeAPI()

        let config = try await api.importLeague(leagueId: "12345", authToken: "fake-token")

        #expect(config.sleeperLeagueId == "12345")
        #expect(config.pointValues["pass_td"] == 6.0)
    }

    @Test func registerDeviceTokenDoesNotThrow() async throws {
        let api = FakeFantaseeAPI()

        try await api.registerDeviceToken("abc123", authToken: "fake-token")
    }
}
