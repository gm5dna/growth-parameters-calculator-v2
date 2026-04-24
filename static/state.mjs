export const appState = {
  lastResults: null,
  lastPayload: null,
  currentChart: null,
};

export function resetAppState() {
  appState.lastResults = null;
  appState.lastPayload = null;
  appState.currentChart = null;
}
