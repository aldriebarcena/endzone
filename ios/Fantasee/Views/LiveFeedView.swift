import SwiftUI

struct LiveFeedView: View {
    // TODO: swap for URLSessionFantaseeAPI once the backend API surface
    // exists (PROJECT_PLAN.md open question). Demo game ID is a stand-in
    // for real game selection, which also needs that surface.
    private let api: FantaseeAPI = FakeFantaseeAPI()

    @State private var gameState: GameStateDTO?
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            List {
                if let gameState {
                    Section("\(gameState.awayTeam) @ \(gameState.homeTeam)") {
                        HStack {
                            Text("\(gameState.awayScore) – \(gameState.homeScore)")
                                .font(.headline)
                            Spacer()
                            Text("\(gameState.period) · \(gameState.clock ?? "")")
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                    Section("Scoring Plays") {
                        ForEach(gameState.events, id: \.eventId) { event in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(event.description)
                                Text("\(event.team) · \(event.scoringType) · \(event.period) \(event.gameClock)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                } else if let errorMessage {
                    Text(errorMessage)
                        .foregroundStyle(.red)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("Live Feed")
            .task {
                await loadGame()
            }
        }
    }

    private func loadGame() async {
        do {
            gameState = try await api.fetchLiveGame(gameId: "demo")
        } catch {
            errorMessage = "Couldn't load game: \(error.localizedDescription)"
        }
    }
}

#Preview {
    LiveFeedView()
}
