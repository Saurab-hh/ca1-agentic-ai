"""Zero-dependency Modern Web Interface for FinAdvisor AI (Loan & EMI Intelligence Agent)."""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from src.agent import LoanAdvisorAgent
from src.config import (
    DEFAULT_AFFORDABILITY_THRESHOLD,
    DEFAULT_MEMORY_FILE,
    GROQ_MODEL,
    GROQ_API_KEY,
)
from src.memory import ConversationMemory

memory = ConversationMemory(DEFAULT_MEMORY_FILE)
agent = LoanAdvisorAgent(memory=memory)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinAdvisor AI | Autonomous Loan & EMI Intelligence Agent</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #070a13;
            --bg-surface: rgba(15, 23, 42, 0.7);
            --bg-surface-elevated: rgba(30, 41, 59, 0.65);
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(99, 102, 241, 0.35);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.25);
            --accent-cyan: #06b6d4;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-rose: #f43f5e;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --gradient-brand: linear-gradient(135deg, #6366f1 0%, #38bdf8 50%, #a855f7 100%);
            --gradient-card: linear-gradient(180deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0) 100%);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(circle at 10% 0%, rgba(99, 102, 241, 0.18) 0%, transparent 45%),
                radial-gradient(circle at 90% 90%, rgba(6, 182, 212, 0.15) 0%, transparent 45%),
                radial-gradient(circle at 50% 50%, rgba(168, 85, 247, 0.06) 0%, transparent 60%);
            background-attachment: fixed;
            overflow-x: hidden;
        }

        /* Top Navigation Header */
        header {
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--border-subtle);
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(16px);
            background: rgba(7, 10, 19, 0.82);
            position: sticky;
            top: 0;
            z-index: 50;
        }

        .brand-container {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            border-radius: 12px;
            background: var(--gradient-brand);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 0 20px var(--primary-glow);
        }

        .brand-info h1 {
            font-size: 1.2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .brand-info p {
            font-size: 0.78rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .engine-pill {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.25);
            padding: 0.4rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.78rem;
            font-weight: 600;
            color: #34d399;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #10b981;
            box-shadow: 0 0 10px #10b981;
            animation: pulseDot 2s infinite ease-in-out;
        }

        @keyframes pulseDot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.85); }
        }

        .btn-ghost {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            color: var(--text-secondary);
            padding: 0.5rem 1rem;
            border-radius: 10px;
            font-family: inherit;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .btn-ghost:hover {
            background: rgba(244, 63, 94, 0.12);
            color: #fda4af;
            border-color: rgba(244, 63, 94, 0.3);
        }

        /* App Grid Layout */
        .app-layout {
            max-width: 1350px;
            margin: 0 auto;
            padding: 1.5rem;
            display: grid;
            grid-template-columns: 340px 1fr;
            gap: 1.5rem;
            flex: 1;
            width: 100%;
        }

        /* Sidebar Panels */
        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .panel {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 18px;
            padding: 1.25rem;
            backdrop-filter: blur(16px);
            position: relative;
            overflow: hidden;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .panel::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 1px;
            background: var(--gradient-card);
        }

        .panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 1rem;
        }

        .panel-title {
            font-size: 0.82rem;
            font-weight: 700;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }

        .metric-card {
            background: rgba(255, 255, 255, 0.025);
            border: 1px solid var(--border-subtle);
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
        }

        .metric-label {
            font-size: 0.72rem;
            color: var(--text-muted);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.25rem;
        }

        .metric-value {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-primary);
            font-family: 'JetBrains Mono', monospace;
        }

        .metric-value.accent {
            color: var(--accent-cyan);
        }

        .metric-value.green {
            color: var(--accent-emerald);
        }

        .guardrail-card {
            background: rgba(99, 102, 241, 0.05);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 12px;
            padding: 0.85rem;
            font-size: 0.8rem;
            line-height: 1.45;
            color: var(--text-secondary);
        }

        .guardrail-card strong {
            color: #c7d2fe;
        }

        /* Preset Prompts */
        .prompt-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .prompt-chip {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-subtle);
            padding: 0.75rem 0.9rem;
            border-radius: 12px;
            font-size: 0.82rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            text-align: left;
            font-family: inherit;
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .prompt-chip .chip-title {
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        .prompt-chip .chip-desc {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .prompt-chip:hover {
            background: rgba(99, 102, 241, 0.12);
            border-color: rgba(99, 102, 241, 0.4);
            color: #c7d2fe;
            transform: translateX(4px);
        }

        /* Main Chat Canvas */
        .chat-canvas {
            display: flex;
            flex-direction: column;
            height: calc(100vh - 120px);
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: 20px;
            overflow: hidden;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 1.75rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            scroll-behavior: smooth;
        }

        .message-row {
            display: flex;
            gap: 0.85rem;
            max-width: 90%;
            animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-row.user {
            align-self: flex-end;
            flex-direction: row-reverse;
        }

        .message-row.agent {
            align-self: flex-start;
            max-width: 92%;
        }

        .avatar {
            width: 36px;
            height: 36px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }

        .avatar.agent-avatar {
            background: var(--gradient-brand);
            box-shadow: 0 0 12px var(--primary-glow);
        }

        .avatar.user-avatar {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--border-subtle);
        }

        .bubble-content {
            display: flex;
            flex-direction: column;
            gap: 0.6rem;
        }

        .message-bubble {
            padding: 1.15rem 1.4rem;
            border-radius: 18px;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .message-row.user .message-bubble {
            background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
            color: #ffffff;
            border-bottom-right-radius: 4px;
            box-shadow: 0 4px 20px rgba(79, 70, 229, 0.3);
        }

        .message-row.agent .message-bubble {
            background: var(--bg-surface-elevated);
            border: 1px solid var(--border-subtle);
            border-bottom-left-radius: 4px;
            color: #f1f5f9;
        }

        /* Formatted Response Elements */
        .message-bubble h2, .message-bubble h3 {
            margin: 0.4rem 0 0.6rem 0;
            color: #ffffff;
            font-size: 1.05rem;
            font-weight: 700;
        }

        .message-bubble strong {
            color: #38bdf8;
            font-weight: 600;
        }

        .message-bubble ul {
            margin: 0.5rem 0 0.5rem 1.25rem;
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }

        .message-bubble blockquote {
            border-left: 3px solid var(--accent-cyan);
            background: rgba(6, 182, 212, 0.08);
            padding: 0.65rem 0.9rem;
            border-radius: 6px;
            font-size: 0.82rem;
            color: #94a3b8;
            margin-top: 0.75rem;
        }

        /* Execution Trace Accordion */
        .trace-card {
            background: #040711;
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 12px;
            overflow: hidden;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
        }

        .trace-toggle {
            padding: 0.65rem 1rem;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            color: var(--text-secondary);
            font-weight: 500;
            transition: background 0.2s;
        }

        .trace-toggle:hover {
            background: rgba(255, 255, 255, 0.05);
            color: #e2e8f0;
        }

        .trace-content {
            padding: 1rem;
            white-space: pre-wrap;
            color: #cbd5e1;
            max-height: 280px;
            overflow-y: auto;
            display: none;
            line-height: 1.6;
        }

        .trace-content.expanded {
            display: block;
        }

        /* Thinking / Loading State */
        .thinking-row {
            display: none;
            align-items: center;
            gap: 0.75rem;
            padding: 0.85rem 1.25rem;
            background: rgba(99, 102, 241, 0.08);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 14px;
            max-width: 320px;
            font-size: 0.82rem;
            color: #c7d2fe;
            margin-bottom: 0.5rem;
        }

        .typing-indicator {
            display: flex;
            gap: 4px;
        }

        .typing-indicator span {
            width: 6px;
            height: 6px;
            background: var(--primary);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }

        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); opacity: 0.3; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* Input Controls */
        .input-wrapper {
            padding: 1.25rem;
            border-top: 1px solid var(--border-subtle);
            background: rgba(7, 10, 19, 0.95);
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }

        .chat-input {
            flex: 1;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-subtle);
            padding: 0.95rem 1.4rem;
            border-radius: 14px;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.95rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .chat-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
            background: rgba(255, 255, 255, 0.07);
        }

        .btn-primary {
            background: var(--gradient-brand);
            border: none;
            color: white;
            padding: 0.95rem 1.6rem;
            border-radius: 14px;
            font-family: inherit;
            font-weight: 700;
            font-size: 0.92rem;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 16px var(--primary-glow);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px var(--primary-glow);
            filter: brightness(1.1);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        @media (max-width: 900px) {
            .app-layout {
                grid-template-columns: 1fr;
            }
            .sidebar {
                display: none;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="brand-container">
            <div class="brand-icon">⚡</div>
            <div class="brand-info">
                <h1>FinAdvisor AI</h1>
                <p>Autonomous Loan & EMI Intelligence Agent</p>
            </div>
        </div>
        <div class="header-actions">
            <div class="engine-pill">
                <span class="status-dot"></span>
                <span>Groq LPU Active</span>
            </div>
            <button class="btn-ghost" onclick="clearMemory()">
                <span>🧹</span> Reset Session
            </button>
        </div>
    </header>

    <div class="app-layout">
        <!-- Left Sidebar: Session Memory & Capabilities -->
        <aside class="sidebar">
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">🧠 Session Context Memory</div>
                </div>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Monthly Income</div>
                        <div class="metric-value accent" id="mem-income">Not Stated</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Existing EMIs</div>
                        <div class="metric-value" id="mem-debts">₹0.00</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Budget (30%)</div>
                        <div class="metric-value green" id="mem-cap">₹0.00/mo</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cached Options</div>
                        <div class="metric-value" id="mem-options">0 profiles</div>
                    </div>
                </div>
                <div class="guardrail-card">
                    <strong>🛡️ Domain Guardrail Active:</strong> Non-financial or out-of-scope queries are identified and handled within loan advisory boundaries.
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">💡 Interactive Presets</div>
                </div>
                <div class="prompt-list">
                    <button class="prompt-chip" onclick="sendChip('I earn ₹60,000 per month. Compare a ₹5 lakh loan for 3 years and 5 years.')">
                        <span class="chip-title">📊 Multi-Tenure Comparison</span>
                        <span class="chip-desc">₹60k income, 5L loan (3y vs 5y)</span>
                    </button>
                    <button class="prompt-chip" onclick="sendChip('What if I pick the longer tenure?')">
                        <span class="chip-title">🔄 Multi-Turn Context Recall</span>
                        <span class="chip-desc">Adjust tenure using conversation memory</span>
                    </button>
                    <button class="prompt-chip" onclick="sendChip('I earn ₹20,000 and want a ₹10 lakh loan for 2 years.')">
                        <span class="chip-title">⚠️ Affordability Cap Test</span>
                        <span class="chip-desc">Triggers 30% heuristic budget alert</span>
                    </button>
                    <button class="prompt-chip" onclick="sendChip('I earn ₹70,000 per month and already pay ₹20,000 in EMIs. Compare a 6 lakh loan for 3 and 5 years.')">
                        <span class="chip-title">💳 Debt-Adjusted Capacity</span>
                        <span class="chip-desc">Accounts for existing monthly obligations</span>
                    </button>
                    <button class="prompt-chip" onclick="sendChip('How to write a binary search tree algorithm in C++?')">
                        <span class="chip-title">🛡️ Out-of-Scope Guardrail</span>
                        <span class="chip-desc">Tests domain boundary enforcement</span>
                    </button>
                </div>
            </div>
        </aside>

        <!-- Right Main Canvas: Chat Stream -->
        <main class="chat-canvas">
            <div class="chat-messages" id="messages">
                <div class="message-row agent">
                    <div class="avatar agent-avatar">⚡</div>
                    <div class="bubble-content">
                        <div class="message-bubble">
                            <h3>👋 Welcome to FinAdvisor AI</h3>
                            I am your intelligent financial reasoning agent powered by <strong>Groq LPU high-speed inference</strong> and <strong>deterministic Python math engines</strong>.<br><br>
                            <strong>What I can do for you:</strong>
                            <ul>
                                <li>Compute reducing-balance EMIs and total interest without math hallucination.</li>
                                <li>Compare multi-year tenure alternatives side-by-side.</li>
                                <li>Evaluate affordability against your monthly income using the 30% heuristic cap.</li>
                                <li>Retain your session context across multi-turn questions.</li>
                            </ul>
                            <br>
                            <em>Try typing a question below or select one of the presets on the left.</em>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Thinking Indicator -->
            <div id="thinking" class="thinking-row" style="margin-left: 1.75rem;">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
                <span>Executing Plan-Act-Observe-Decide cycle...</span>
            </div>

            <div class="input-wrapper">
                <input type="text" id="query-input" class="chat-input" placeholder="E.g., 'I earn 65000. Compare a 5 lakh loan for 3 years and 5 years at 10% rate'..." onkeydown="if(event.key==='Enter') sendMessage()">
                <button class="btn-primary" onclick="sendMessage()">
                    <span>Send</span> ➔
                </button>
            </div>
        </main>
    </div>

    <script>
        async function fetchMemory() {
            try {
                const res = await fetch('/api/memory');
                const data = await res.json();
                const income = data.monthly_income;
                const debts = data.existing_obligations || 0;
                
                document.getElementById('mem-income').innerText = income ? '₹' + Number(income).toLocaleString('en-IN') : 'Not Stated';
                document.getElementById('mem-debts').innerText = '₹' + Number(debts).toLocaleString('en-IN');
                
                if (income) {
                    const disposable = Math.max(0, income - debts);
                    const cap = disposable * 0.30;
                    document.getElementById('mem-cap').innerText = '₹' + Number(cap).toLocaleString('en-IN', {maximumFractionDigits: 0}) + '/mo';
                } else {
                    document.getElementById('mem-cap').innerText = '30% Heuristic';
                }
                
                document.getElementById('mem-options').innerText = (data.previously_seen_options || []).length + ' profiles';
            } catch(e) {}
        }

        async function clearMemory() {
            await fetch('/api/clear', { method: 'POST' });
            fetchMemory();
            appendMessage('agent', '🧹 <em>Conversation session memory has been reset to default.</em>');
        }

        function sendChip(text) {
            document.getElementById('query-input').value = text;
            sendMessage();
        }

        function formatMarkdown(text) {
            if (!text) return '';
            let html = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // Bold
            html = html.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
            
            // Blockquotes
            html = html.replace(/^>\s*\\*(.*?)\\*$/gm, '<blockquote>$1</blockquote>');
            html = html.replace(/^>\s*(.*?)$/gm, '<blockquote>$1</blockquote>');
            
            // Unordered list items
            html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
            html = html.replace(/(<li>.*?<\\/li>)/gs, '<ul>$1</ul>');
            
            // Line breaks
            html = html.replace(/\\n/g, '<br>');
            return html;
        }

        function appendMessage(role, text, trace) {
            const container = document.getElementById('messages');
            const row = document.createElement('div');
            row.className = 'message-row ' + role;
            
            const avatar = document.createElement('div');
            avatar.className = 'avatar ' + (role === 'agent' ? 'agent-avatar' : 'user-avatar');
            avatar.innerHTML = role === 'agent' ? '⚡' : '👤';
            
            const content = document.createElement('div');
            content.className = 'bubble-content';
            
            let bubbleHtml = `<div class="message-bubble">${formatMarkdown(text)}</div>`;
            
            if (trace) {
                const traceId = 'trace-' + Math.random().toString(36).substr(2, 9);
                bubbleHtml += `
                    <div class="trace-card">
                        <div class="trace-toggle" onclick="toggleTrace('${traceId}')">
                            <span>🔍 Multi-Step Execution Trace</span>
                            <span id="${traceId}-icon">▼</span>
                        </div>
                        <div class="trace-content" id="${traceId}">${trace.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</div>
                    </div>
                `;
            }
            
            content.innerHTML = bubbleHtml;
            row.appendChild(avatar);
            row.appendChild(content);
            container.appendChild(row);
            container.scrollTop = container.scrollHeight;
        }

        function toggleTrace(id) {
            const body = document.getElementById(id);
            const icon = document.getElementById(id + '-icon');
            if (body.classList.contains('expanded')) {
                body.classList.remove('expanded');
                icon.innerText = '▼';
            } else {
                body.classList.add('expanded');
                icon.innerText = '▲';
            }
        }

        async function sendMessage() {
            const input = document.getElementById('query-input');
            const query = input.value.trim();
            if (!query) return;

            appendMessage('user', query);
            input.value = '';
            
            const thinking = document.getElementById('thinking');
            thinking.style.display = 'flex';
            const container = document.getElementById('messages');
            container.scrollTop = container.scrollHeight;

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });
                const data = await res.json();
                thinking.style.display = 'none';
                appendMessage('agent', data.answer, data.trace);
                fetchMemory();
            } catch(e) {
                thinking.style.display = 'none';
                appendMessage('agent', '⚠️ Error communicating with agent server: ' + e.message);
            }
        }

        fetchMemory();
    </script>
</body>
</html>
"""


class WebHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP request handler."""

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif parsed.path == "/api/memory":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(memory.to_dict()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = (
            self.rfile.read(content_length).decode("utf-8")
            if content_length > 0
            else "{}"
        )

        if parsed.path == "/api/chat":
            try:
                data = json.loads(body)
                query = data.get("query", "")
                result = agent.run(query)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode("utf-8"))
            except Exception as err:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))

        elif parsed.path == "/api/clear":
            memory.clear()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "cleared"}).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: tuple) -> None:
        """Suppress noisy default request logging in console."""
        pass


def run_server(port: int = 8000) -> None:
    """Launch local web server."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, WebHandler)
    print("=" * 72)
    print(f"[*] FinAdvisor AI Web App running live at: http://localhost:{port}")
    print("=" * 72)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port)
