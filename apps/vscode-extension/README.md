# Dependency Guardian — VS Code Extension

Official VS Code extension for **Dependency Guardian**: proactive API breaking change detection and automated compatibility management.

---

## Features

- **Proactive Specification Comparison**: Compare baseline and current OpenAPI (3.0.x, 3.1.x, Swagger 2.0) specifications directly from VS Code.
- **Three Detection Modes**:
  - `algorithmic` *(Default, Safe)*: Deterministic offline schema comparator. Requires zero AI keys, network access, or external dependencies.
  - `hybrid`: Authoritative deterministic findings enriched with AI reasoning.
  - `ai`: Semantic analysis through configured AI provider (`mock`, `ollama`, or `hosted`).
- **Interactive Mode Switching**: Switch detection modes on the fly via the Status Bar or Command Palette (`Dependency Guardian: Change Detection Mode`), persisting across IDE reloads.
- **Bundled Detection Agent**: Ships with a pre-packaged standalone agent binary in `bin/` so users do not need to install Python or configure virtual environments.
- **Backend Lifecycle Integration**: Check connectivity and sync findings, observations, and incidents to the Dependency Guardian FastAPI backend.

---

## Commands

- `Dependency Guardian: Run Specification Detection`: Select baseline and current OpenAPI specification files, run detection, and review categorized findings in the Output channel.
- `Dependency Guardian: Change Detection Mode`: Interactive QuickPick to switch between `algorithmic`, `hybrid`, and `ai` modes.
- `Dependency Guardian: Check Backend Connection`: Ping the configured FastAPI backend health endpoint.

---

## Configuration Settings

Configure via VS Code Settings (`Ctrl+,` or `Cmd+,` searching for `dependencyGuardian`):

| Setting | Type | Default | Description |
|---|---|---|---|
| `dependencyGuardian.detectionMode` | `string` | `"algorithmic"` | Active detection mode: `algorithmic`, `hybrid`, or `ai`. |
| `dependencyGuardian.aiProvider` | `string` | `"mock"` | AI provider (`mock`, `ollama`, or `hosted`). |
| `dependencyGuardian.backendUrl` | `string` | `"http://127.0.0.1:8000/api/v1"` | URL of the Dependency Guardian FastAPI backend. |
| `dependencyGuardian.agentPath` | `string` | `""` | Optional custom path to agent binary. Leave empty for auto-detection. |
| `dependencyGuardian.pythonPath` | `string` | `"python"` | Python interpreter path used if falling back to python module execution. |

---

## Agent Resolution Precedence

When running detection, the extension resolves the agent executable in the following order:
1. Custom path specified in `dependencyGuardian.agentPath`.
2. Bundled standalone binary inside the extension's `bin/` directory (`dependency-guardian.exe` on Windows, `dependency-guardian` on Linux/macOS).
3. Global CLI command `dependency-guardian` in the user's `PATH`.
4. Python module invocation (`python -m dependency_guardian.cli`).

---

## Development & Packaging

### Prerequisites
- Node.js (v18+) and npm

### Build Extension Bundle
```bash
npm install
npm run build
```

### Run Tests
```bash
npm test
```

### Package VSIX
```bash
npx @vscode/vsce package --no-dependencies
```

### Install VSIX Locally
```bash
code --install-extension dependency-guardian-vscode-0.1.0.vsix
```
