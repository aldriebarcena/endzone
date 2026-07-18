import SwiftUI

struct LeagueImportView: View {
    @Environment(\.fantaseeAPI) private var api
    @Environment(AuthManager.self) private var authManager
    @Environment(\.dismiss) private var dismiss

    @State private var leagueId = ""
    @State private var isImporting = false
    @State private var errorMessage: String?
    @State private var importedLeague: LeagueConfigDTO?

    var body: some View {
        NavigationStack {
            Form {
                Section("Sleeper League ID") {
                    TextField("e.g. 289646328504385536", text: $leagueId)
                        .keyboardType(.numberPad)
                        .disabled(isImporting)
                }

                if let importedLeague {
                    Section("Imported") {
                        LabeledContent("League", value: importedLeague.leagueName)
                        LabeledContent("Season", value: importedLeague.season)
                        LabeledContent("Scoring categories", value: "\(importedLeague.pointValues.count)")
                    }
                }

                if let errorMessage {
                    Text(errorMessage).foregroundStyle(.red)
                }
            }
            .navigationTitle("Import League")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    if isImporting {
                        ProgressView()
                    } else {
                        Button("Import") { Task { await importLeague() } }
                            .disabled(leagueId.isEmpty)
                    }
                }
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
    }

    private func importLeague() async {
        // authToken is required by the backend's JWT authorizer (see
        // backend/template.yaml FantaseeHttpApi) — a signed-out user
        // can't reach this view via LiveFeedView's normal flow, but the
        // guard keeps this view correct on its own regardless of how
        // it's presented.
        guard let authToken = authManager.identityToken else {
            errorMessage = "Not signed in"
            return
        }

        isImporting = true
        errorMessage = nil
        defer { isImporting = false }

        do {
            importedLeague = try await api.importLeague(leagueId: leagueId, authToken: authToken)
        } catch {
            errorMessage = "Couldn't import league: \(error.localizedDescription)"
        }
    }
}

#Preview {
    LeagueImportView()
        .environment(AuthManager())
}
