import SwiftUI

struct LiveFeedView: View {
    @Environment(\.fantaseeAPI) private var api

    @State private var gameState: GameStateDTO?
    @State private var errorMessage: String?
    @State private var showingLeagueImport = false

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
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Import League") { showingLeagueImport = true }
                }
            }
            .sheet(isPresented: $showingLeagueImport) {
                LeagueImportView()
            }
            .task {
                await loadGame()
            }
        }
    }

    private func loadGame() async {
        // Demo game ID stands in for real game selection, which needs
        // the same missing per-user context as league selection did
        // (see PROJECT_PLAN.md's checker open question).
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
