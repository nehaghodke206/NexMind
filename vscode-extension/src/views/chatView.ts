import * as vscode from "vscode";
import { GuardianClient } from "../api/guardianClient";
import { AgentRunner } from "../agents/agentRunner";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  isError?: boolean;
}

export class GuardianChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "dependencyGuardian.chatView";
  private _view?: vscode.WebviewView;
  private _messages: ChatMessage[] = [];

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly client: GuardianClient,
    private readonly agentRunner?: AgentRunner
  ) {
    // Initial welcome message
    this._messages.push({
      id: "msg_welcome",
      role: "assistant",
      content:
        `### Guardian Assistant (UI Preview)\n` +
        `Welcome to Dependency Guardian. I can help you monitor API contract drifts, inspect breaking changes, and guide you through safe backwards-compatible repairs.\n\n` +
        `> **Adapter Status:** Direct conversational LLM chat is awaiting a backend \`/chat\` endpoint. ` +
        `This UI-ready diagnostic adapter provides workspace guidance and live status without fabricating AI output.\n\n` +
        `Try asking about:\n` +
        `- **"status"**: Check live backend and dependency health\n` +
        `- **"detect"**: Learn how contract drift detection works\n` +
        `- **"repair"**: Understand the repair pipeline and safety approvals\n` +
        `- **"help"**: View available commands and quick actions`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    });
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this._getHtmlForWebview();

    webviewView.webview.onDidReceiveMessage(async (message) => {
      switch (message.command) {
        case "sendMessage":
          await this.handleUserMessage(message.text);
          break;
        case "clearHistory":
          this.clearHistory();
          break;
        case "openDashboard":
          vscode.commands.executeCommand("dependencyGuardian.openDashboard");
          break;
        case "executeCommand":
          if (message.commandId) {
            vscode.commands.executeCommand(message.commandId);
          }
          break;
        case "copyToClipboard":
          if (message.text) {
            await vscode.env.clipboard.writeText(message.text);
            vscode.window.showInformationMessage("Code copied to clipboard.");
          }
          break;
      }
    });

    // Ensure the main dashboard is opened/revealed in the main editor area
    vscode.commands.executeCommand("dependencyGuardian.openDashboard");
    webviewView.onDidChangeVisibility(() => {
      if (webviewView.visible) {
        vscode.commands.executeCommand("dependencyGuardian.openDashboard");
      }
    });

    // Send existing messages on load
    this.syncMessagesToWebview();
  }

  public getMessages(): ChatMessage[] {
    return [...this._messages];
  }

  public clearHistory(): void {
    this._messages = [
      {
        id: `msg_${Date.now()}`,
        role: "system",
        content: "Chat session history cleared.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ];
    this.syncMessagesToWebview();
  }

  public async handleUserMessage(rawText: string): Promise<void> {
    const text = (rawText || "").trim();
    if (!text) {
      return;
    }

    const userMsg: ChatMessage = {
      id: `msg_u_${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    this._messages.push(userMsg);
    this.syncMessagesToWebview();

    // Signal loading in webview
    if (this._view) {
      this._view.webview.postMessage({ type: "setLoading", loading: true });
    }

    try {
      // Process through Diagnostic & Guidance Placeholder Adapter
      const replyContent = await this.generateAdapterResponse(text);

      const assistantMsg: ChatMessage = {
        id: `msg_a_${Date.now()}`,
        role: "assistant",
        content: replyContent,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      this._messages.push(assistantMsg);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg_err_${Date.now()}`,
        role: "assistant",
        content: `**Error:** Failed to process query: ${err.message || String(err)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        isError: true,
      };
      this._messages.push(errorMsg);
    } finally {
      if (this._view) {
        this._view.webview.postMessage({ type: "setLoading", loading: false });
      }
      this.syncMessagesToWebview();
    }
  }

  private async generateAdapterResponse(prompt: string): Promise<string> {
    const lower = prompt.toLowerCase();

    // Small async pause to give realistic UI response cycle
    await new Promise((resolve) => setTimeout(resolve, 350));

    if (lower.includes("status") || lower.includes("health") || lower.includes("backend")) {
      let isOnline = false;
      let error = "";
      try {
        await this.client.getHealth();
        isOnline = true;
      } catch (err: any) {
        error = err.message || "Unreachable";
      }

      let changesCount = 0;
      if (isOnline) {
        try {
          const changes = await this.client.getChanges();
          changesCount = changes.length;
        } catch {}
      }

      return (
        `### Workspace Health Diagnostics\n\n` +
        `- **Backend URL:** \`${this.client.getBaseUrl()}\`\n` +
        `- **Status:** ${isOnline ? "🟢 **Online**" : `🔴 **Offline** (${error})`}\n` +
        `- **Detected Incidents:** ${changesCount}\n\n` +
        (isOnline
          ? `Everything is communicating properly with the backend.`
          : `⚠️ **Action Required:** Ensure the backend service is running:\n` +
            `\`\`\`bash\ncd services/backend && uvicorn app.main:app --port 8000\n\`\`\``)
      );
    }

    if (lower.includes("detect") || lower.includes("drift") || lower.includes("scan")) {
      return (
        `### Contract Drift Detection\n\n` +
        `The Detection Agent compares baseline OpenAPI specifications against active versions to find breaking changes (e.g. removed fields, type changes, missing endpoints).\n\n` +
        `**CLI Invocation:**\n` +
        `\`\`\`bash\npython -m dependency_guardian detect \\\n  --baseline contracts/openapi-v1.json \\\n  --current contracts/openapi-v2.json \\\n  --sync-backend\n\`\`\`\n\n` +
        `You can trigger detection directly inside VS Code via **Run Contract Drift Detection**.`
      );
    }

    if (lower.includes("repair") || lower.includes("fix") || lower.includes("patch")) {
      return (
        `### Backward-Compatible Repairs\n\n` +
        `Dependency Guardian uses a hybrid repair pipeline:\n` +
        `1. **Deterministic Adapters:** Fast, exact AST transformations (e.g. \`dict.get()\` fallbacks, query params).\n` +
        `2. **LLM Generation:** Local Ollama (\`qwen2.5-coder:3b\`) with sandboxed validation.\n` +
        `3. **Human-in-the-Loop:** Strict diff-review and cryptographic SHA-256 patch binding before any changes are applied.\n\n` +
        `**CLI Invocation:**\n` +
        `\`\`\`bash\npython -m repair_agent repair \\\n  --incident-id <INCIDENT_ID> \\\n  --sync-backend\n\`\`\``
      );
    }

    if (lower.includes("help") || lower.includes("command") || lower.includes("action")) {
      return (
        `### Available Guardian Commands\n\n` +
        `| Command | Description |\n` +
        `| :--- | :--- |\n` +
        `| \`dependencyGuardian.runDetection\` | Run contract drift detection |\n` +
        `| \`dependencyGuardian.openDashboard\` | Open full editor dashboard |\n` +
        `| \`dependencyGuardian.reviewRepair\` | Review repair proposal diff |\n` +
        `| \`dependencyGuardian.approveRepair\` | Approve validated repair |\n` +
        `| \`dependencyGuardian.applyRepair\` | Safely apply approved changes |\n` +
        `| \`dependencyGuardian.setupEnvironment\` | Verify Python & agent setup |\n\n` +
        `All commands are also accessible via the Command Palette (\`Ctrl+Shift+P\` or \`Cmd+Shift+P\`).`
      );
    }

    // Default honest placeholder response
    return (
      `**[Guardian Assistant — Diagnostic & Guidance Adapter]**\n\n` +
      `Direct interactive conversational AI is planned for a future update (no backend \`/chat\` endpoint is currently exposed). ` +
      `Guardian does not fabricate AI reasoning to avoid misleading diagnostics.\n\n` +
      `You can use the following verified actions in this workspace:\n` +
      `- Type **"status"** to test live backend connection.\n` +
      `- Type **"detect"** or **"repair"** for pipeline details and commands.\n` +
      `- Type **"help"** for a full list of registered VS Code commands.\n\n` +
      `*Query received:* "${prompt}"`
    );
  }

  private syncMessagesToWebview(): void {
    if (this._view) {
      this._view.webview.postMessage({
        type: "updateMessages",
        messages: this._messages,
      });
    }
  }

  private _getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <title>Guardian Assistant</title>
  <style>
    :root {
      --bg-surface: var(--vscode-editor-background, #1E1E1E);
      --card-surface: var(--vscode-sideBar-background, #252526);
      --input-surface: var(--vscode-input-background, #2D2D30);
      --hover-surface: var(--vscode-list-hoverBackground, #37373D);
      --border-subtle: var(--vscode-widget-border, #3E3E42);
      --border-focus: var(--vscode-focusBorder, #007ACC);
      --text-main: var(--vscode-editor-foreground, #CCCCCC);
      --text-muted: var(--vscode-descriptionForeground, #8E8E93);
      --accent: var(--vscode-button-background, #0E639C);
      --accent-hover: var(--vscode-button-hoverBackground, #1177BB);
      --code-bg: var(--vscode-textCodeBlock-background, #1E1E1E);
      --user-bubble: var(--input-surface);
      --user-border: var(--border-subtle);
      --assistant-bubble: var(--card-surface);
      --assistant-border: var(--border-subtle);
      --danger: var(--vscode-errorForeground, #F14C4C);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      background-color: var(--bg-surface);
      color: var(--text-main);
      font-family: var(--vscode-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
      font-size: var(--vscode-font-size, 12px);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    .chat-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 12px;
      background: var(--card-surface);
      border-bottom: 1px solid var(--border-subtle);
      flex-shrink: 0;
    }

    .chat-header-title {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .badge-preview {
      font-size: 9px;
      font-weight: 500;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      padding: 1px 5px;
      border-radius: 2px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }

    .header-actions {
      display: flex;
      gap: 6px;
    }

    .header-btn {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      cursor: pointer;
      font-size: 10px;
      padding: 2px 6px;
      border-radius: 2px;
      font-family: inherit;
    }

    .header-btn:hover {
      background: var(--hover-surface);
      color: var(--text-main);
    }

    .messages-container {
      flex: 1;
      overflow-y: auto;
      padding: 12px 10px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .message-row {
      display: flex;
      flex-direction: column;
      max-width: 100%;
    }

    .message-row.user {
      align-items: flex-end;
    }

    .message-row.assistant, .message-row.system {
      align-items: flex-start;
    }

    .message-meta {
      font-size: 10px;
      color: var(--text-muted);
      margin-bottom: 3px;
      padding: 0 4px;
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .bubble {
      padding: 7px 10px;
      border-radius: 3px;
      line-height: 1.45;
      word-break: break-word;
      font-size: 12px;
      max-width: 95%;
    }

    .message-row.user .bubble {
      background: var(--user-bubble);
      border: 1px solid var(--user-border);
      color: var(--text-main);
    }

    .message-row.assistant .bubble {
      background: var(--assistant-bubble);
      border: 1px solid var(--assistant-border);
      color: var(--text-main);
    }

    .message-row.assistant.error .bubble {
      border-color: rgba(239, 68, 68, 0.5);
      background: rgba(239, 68, 68, 0.1);
      color: #FCA5A5;
    }

    .message-row.system .bubble {
      background: transparent;
      border: 1px dashed var(--border-subtle);
      color: var(--text-muted);
      font-style: italic;
      font-size: 11px;
      padding: 6px 8px;
    }

    /* Formatting inside markdown */
    .bubble p { margin-bottom: 6px; }
    .bubble p:last-child { margin-bottom: 0; }
    .bubble ul, .bubble ol { margin: 6px 0 6px 16px; }
    .bubble li { margin-bottom: 3px; }
    .bubble blockquote {
      border-left: 3px solid var(--accent);
      padding-left: 8px;
      margin: 6px 0;
      color: var(--text-muted);
      font-size: 11px;
    }
    .bubble h3 {
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 6px;
      color: #FFFFFF;
    }
    .bubble table {
      border-collapse: collapse;
      width: 100%;
      margin: 8px 0;
      font-size: 11px;
    }
    .bubble th, .bubble td {
      border: 1px solid var(--border-subtle);
      padding: 4px 6px;
      text-align: left;
    }
    .bubble th {
      background: var(--input-surface);
      font-weight: 600;
    }

    /* Code blocks */
    .code-container {
      background: var(--code-bg);
      border: 1px solid var(--border-subtle);
      border-radius: 5px;
      margin: 8px 0;
      overflow: hidden;
    }

    .code-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #18181B;
      padding: 3px 8px;
      font-size: 10px;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-subtle);
    }

    .copy-btn {
      background: var(--input-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 10px;
      cursor: pointer;
    }

    .copy-btn:hover {
      background: var(--hover-surface);
    }

    .code-content {
      padding: 8px;
      overflow-x: auto;
      font-family: Consolas, "Courier New", monospace;
      font-size: 11px;
      line-height: 1.4;
      white-space: pre;
    }

    .inline-code {
      background: var(--code-bg);
      border: 1px solid var(--border-subtle);
      padding: 1px 4px;
      border-radius: 3px;
      font-family: Consolas, monospace;
      font-size: 11px;
    }

    /* Action buttons in bubbles */
    .quick-actions-row {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      margin-top: 8px;
    }

    .chip-btn {
      background: var(--input-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .chip-btn:hover {
      background: var(--hover-surface);
      border-color: #52525B;
    }

    /* Loading state */
    .loading-row {
      display: none;
      align-items: center;
      gap: 8px;
      color: var(--text-muted);
      font-size: 11px;
      padding: 4px 6px;
    }

    .loading-dots {
      display: inline-flex;
      gap: 4px;
    }

    .dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--text-muted);
      animation: pulse 1.2s infinite ease-in-out;
    }

    .dot:nth-child(2) { animation-delay: 0.2s; }
    .dot:nth-child(3) { animation-delay: 0.4s; }

    @keyframes pulse {
      0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
      40% { opacity: 1; transform: scale(1.1); }
    }

    /* Input Footer */
    .input-footer {
      padding: 10px;
      background: var(--card-surface);
      border-top: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex-shrink: 0;
    }

    .input-box {
      width: 100%;
      min-height: 54px;
      max-height: 120px;
      background: var(--input-surface);
      color: var(--text-main);
      border: 1px solid var(--border-subtle);
      border-radius: 5px;
      padding: 8px;
      font-family: inherit;
      font-size: 12px;
      resize: vertical;
      line-height: 1.4;
      outline: none;
    }

    .input-box:focus {
      border-color: var(--accent);
    }

    .input-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .input-hint {
      font-size: 10px;
      color: var(--text-muted);
    }

    .send-btn {
      background: var(--accent);
      color: #FFFFFF;
      border: 1px solid var(--accent);
      border-radius: 4px;
      padding: 5px 14px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: background 0.12s ease;
    }

    .send-btn:hover {
      background: var(--accent-hover);
    }

    .send-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <div class="chat-header">
    <div class="chat-header-title">
      <span>Guardian Assistant</span>
      <span class="badge-preview">Diagnostic Preview</span>
    </div>
    <div class="header-actions">
      <button class="header-btn" onclick="openDashboard()">Dashboard ↗</button>
      <button class="header-btn" onclick="clearChat()">Clear</button>
    </div>
  </div>

  <div id="messagesContainer" class="messages-container"></div>

  <div id="loadingRow" class="loading-row">
    <div class="loading-dots">
      <div class="dot"></div>
      <div class="dot"></div>
      <div class="dot"></div>
    </div>
    <span>Guardian is evaluating...</span>
  </div>

  <div class="input-footer">
    <textarea
      id="chatInput"
      class="input-box"
      placeholder="Ask about detected contract drifts, repair strategies, or status... (Enter to send, Shift+Enter for newline)"
    ></textarea>
    <div class="input-controls">
      <span class="input-hint">Shift+Enter for newline</span>
      <button id="sendBtn" class="send-btn" onclick="sendMessage()">Send ➔</button>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const messagesContainer = document.getElementById('messagesContainer');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const loadingRow = document.getElementById('loadingRow');

    function scrollToBottom() {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function openDashboard() {
      vscode.postMessage({ command: 'openDashboard' });
    }

    function clearChat() {
      vscode.postMessage({ command: 'clearHistory' });
    }

    function runCommand(commandId) {
      vscode.postMessage({ command: 'executeCommand', commandId });
    }

    function copyCode(text, btn) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
          btn.textContent = 'Copied!';
          setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
        }).catch(() => {
          vscode.postMessage({ command: 'copyToClipboard', text });
          btn.textContent = 'Copied!';
          setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
        });
      } else {
        vscode.postMessage({ command: 'copyToClipboard', text });
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 1800);
      }
    }

    function sendMessage() {
      const text = chatInput.value.trim();
      if (!text) {
        return;
      }
      vscode.postMessage({ command: 'sendMessage', text });
      chatInput.value = '';
      sendBtn.disabled = true;
    }

    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    chatInput.addEventListener('input', () => {
      const hasText = chatInput.value.trim().length > 0;
      sendBtn.disabled = !hasText;
    });

    window.addEventListener('message', (event) => {
      const msg = event.data;
      if (msg.type === 'updateMessages') {
        renderMessages(msg.messages);
      } else if (msg.type === 'setLoading') {
        if (msg.loading) {
          loadingRow.style.display = 'flex';
          sendBtn.disabled = true;
          chatInput.disabled = true;
        } else {
          loadingRow.style.display = 'none';
          chatInput.disabled = false;
          sendBtn.disabled = chatInput.value.trim().length === 0;
          chatInput.focus();
        }
        scrollToBottom();
      }
    });

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }

    function formatMarkdown(text) {
      if (!text) return '';

      // Extract code blocks first to protect them
      const codeBlocks = [];
      let formatted = text.replace(/\`\`\`([a-zA-Z0-9_-]*)\n([\s\S]*?)\`\`\`/g, (match, lang, code) => {
        const id = '__CODE_BLOCK_' + codeBlocks.length + '__';
        codeBlocks.push({ lang: lang || 'text', code: code.trim() });
        return id;
      });

      // Escape all HTML
      formatted = escapeHtml(formatted);

      // Restore and format code blocks
      codeBlocks.forEach((item, index) => {
        const id = '__CODE_BLOCK_' + index + '__';
        const escapedCode = escapeHtml(item.code);
        const codeBlockHtml = \`
          <div class="code-container">
            <div class="code-header">
              <span>\${escapeHtml(item.lang)}</span>
              <button class="copy-btn" onclick="copyCode(decodeURIComponent('\${encodeURIComponent(item.code)}'), this)">Copy</button>
            </div>
            <div class="code-content">\${escapedCode}</div>
          </div>
        \`;
        formatted = formatted.replace(id, codeBlockHtml);
      });

      // Inline code
      formatted = formatted.replace(/\`([^\`]+)\`/g, '<code class="inline-code">$1</code>');

      // Headers
      formatted = formatted.replace(/^### (.*$)/gim, '<h3>$1</h3>');
      formatted = formatted.replace(/^## (.*$)/gim, '<h3>$1</h3>');

      // Bold & Italic
      formatted = formatted.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
      formatted = formatted.replace(/\\*(.*?)\\*/g, '<em>$1</em>');

      // Blockquotes
      formatted = formatted.replace(/^> (.*$)/gim, '<blockquote>$1</blockquote>');

      // Unordered lists
      formatted = formatted.replace(/^\\s*-\\s+(.*$)/gim, '<li>$1</li>');
      formatted = formatted.replace(/(<li>[\\s\\S]*?<\\/li>)/g, '<ul>$1</ul>');

      // Paragraph newlines (except inside pre/code)
      formatted = formatted.replace(/\\n\\n/g, '<p></p>');
      formatted = formatted.replace(/\\n/g, '<br>');

      return formatted;
    }

    function renderMessages(messages) {
      messagesContainer.innerHTML = '';
      (messages || []).forEach((m) => {
        const row = document.createElement('div');
        row.className = 'message-row ' + m.role + (m.isError ? ' error' : '');

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const roleLabel = m.role === 'user' ? 'You' : (m.role === 'assistant' ? 'Guardian Assistant' : 'System');
        meta.innerHTML = '<span>' + roleLabel + '</span><span>' + escapeHtml(m.timestamp) + '</span>';

        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.innerHTML = formatMarkdown(m.content);

        row.appendChild(meta);
        row.appendChild(bubble);
        messagesContainer.appendChild(row);
      });

      scrollToBottom();
    }
  </script>
</body>
</html>`;
  }
}
