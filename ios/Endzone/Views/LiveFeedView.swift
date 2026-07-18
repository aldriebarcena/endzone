import SwiftUI

struct LiveFeedView: View {
    @Environment(\.endzoneAPI) private var api
    @Environment(AuthManager.self) private var authManager

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
                                // The actual point of the app: real
                                // per-player fantasy points, computed
                                // against the signed-in user's own
                                // league scoring settings (empty when
                                // the play type isn't scored yet, or no
                                // league's been imported).
                                ForEach(pointsBreakdown(for: event), id: \.playerId) { entry in
                                    Text("\(entry.name) +\(entry.points, specifier: "%.2f") pts")
                                        .font(.subheadline.bold())
                                        .foregroundStyle(.green)
                                }
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
        guard let authToken = authManager.identityToken else {
            errorMessage = "Not signed in"
            return
        }
        do {
            gameState = try await api.fetchLiveGame(authToken: authToken)
        } catch {
            errorMessage = "Couldn't load game: \(error.localizedDescription)"
        }
    }

    private func pointsBreakdown(for event: ScoringEventDTO) -> [(playerId: String, name: String, points: Double)] {
        event.points
            .map { playerId, points in
                (playerId: playerId, name: event.playerNames[playerId] ?? playerId, points: points)
            }
            .sorted { $0.points > $1.points }
    }
}

#Preview {
    LiveFeedView()
        .environment(AuthManager())
}
