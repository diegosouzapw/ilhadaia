/**
 * benchmark.js — T16: Lógica do HUD de Benchmark, Replay, Modal e Timeline.
 * Carregado ANTES de main.js para que as funções estejam disponíveis.
 */

// ─── Estado do replay ─────────────────────────────────────────────────────────
let replayFrames = [];
let replayIndex = 0;
let replayInterval = null;
const REPLAY_FPS_MS = 300; // 300ms por frame = ~3 FPS

function getApiBaseUrl() {
    const host = window.location.hostname || 'localhost';
    const backendPortOverride =
        new URLSearchParams(window.location.search).get('backend_port') ||
        localStorage.getItem('bbb_backend_port');
    if (backendPortOverride) {
        return `http://${host}:${backendPortOverride}`;
    }
    if (window.location.protocol === 'file:') {
        return `http://${host}:8001`;
    }
    const port = window.location.port === '3000' ? '8000' : (window.location.port || '8000');
    return `http://${host}:${port}`;
}

const BENCHMARK_API_BASE_URL = getApiBaseUrl();

// ─── HUD de Benchmark ─────────────────────────────────────────────────────────

/**
 * Atualiza a tabela de benchmark com os dados dos agentes recebidos via WS.
 * Chamado pelo main.js quando chega uma mensagem de update.
 */
function updateBenchmarkHUD(agents, sessionId) {
    const tbody = document.getElementById('benchmark-body');
    if (!tbody || !agents || agents.length === 0) return;

    // Atualizar session ID
    const sidEl = document.getElementById('session-id-display');
    if (sidEl && sessionId) sidEl.textContent = sessionId.slice(0, 12) + '…';

    // Ordenar por score
    const sorted = [...agents].sort((a, b) => {
        const sa = a.benchmark?.score ?? 0;
        const sb = b.benchmark?.score ?? 0;
        return sb - sa;
    });

    tbody.innerHTML = sorted.map((a, i) => {
        const isDead = !a.is_alive;
        const tokens = a.tokens_used ?? 0;
        const budget = a.token_budget ?? 10000;
        const tokenPct = Math.min(100, (tokens / budget) * 100);
        const score = (a.benchmark?.score ?? 0).toFixed(1);
        const hp = a.hp ?? 0;
        const model = a.profile_id ?? 'gemini';
        const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i+1}.`;

        return `<tr class="${isDead ? 'agent-dead' : ''}" onclick="showAgentModal('${a.id}')" title="Ver detalhes">
            <td><span class="medal">${medal}</span> ${a.name}</td>
            <td><small class="model-badge">${model}</small></td>
            <td>
                <div class="token-bar-wrap" title="${tokens}/${budget} tokens">
                    <div class="token-bar" style="width:${tokenPct}%"></div>
                </div>
                <span style="font-size:10px;color:#aaa">${(tokens/1000).toFixed(1)}k</span>
            </td>
            <td class="score-cell">${score}</td>
            <td><span class="hp-badge" style="color:${hp > 50 ? '#4caf50' : hp > 20 ? '#ff9800' : '#f44336'}">${hp}</span></td>
        </tr>`;
    }).join('');
}

// ─── Modal de Agente ──────────────────────────────────────────────────────────

async function showAgentModal(agentId) {
    // Só busca API se não for replay
    let state;
    try {
        const resp = await fetch(`${BENCHMARK_API_BASE_URL}/agents/${agentId}/state`);
        if (!resp.ok) throw new Error('not found');
        state = await resp.json();
    } catch {
        return;
    }

    const modal = document.getElementById('agent-modal');
    const modalName = document.getElementById('modal-agent-name');
    const modalBody = document.getElementById('modal-body');

    modalName.textContent = `${state.name}`;

    const tokenPct = Math.min(100, ((state.tokens_used/state.token_budget)*100)).toFixed(1);
    const bm = state.benchmark ?? {};

    modalBody.innerHTML = `
        <div class="modal-row"><span class="modal-label">Perfil</span><span class="modal-value">${state.profile_id}</span></div>
        <div class="modal-row">
            <span class="modal-label">Budget</span>
            <span class="modal-value">
                <div class="token-bar-wrap" style="width:120px; display:inline-block;">
                    <div class="token-bar" style="width:${tokenPct}%"></div>
                </div>
                ${state.tokens_used.toLocaleString()} / ${state.token_budget.toLocaleString()} tokens (${tokenPct}%)
            </span>
        </div>
        <div class="modal-row"><span class="modal-label">Score</span><span class="modal-value score-cell">${(bm.score??0).toFixed(2)}</span></div>
        <div class="modal-row"><span class="modal-label">Decisões</span><span class="modal-value">${bm.decisions_made??0} (${bm.invalid_actions??0} inválidas)</span></div>
        <div class="modal-row"><span class="modal-label">Ticks vivo</span><span class="modal-value">${bm.ticks_survived??0}</span></div>
        <div class="modal-row"><span class="modal-label">HP</span><span class="modal-value">${state.health}</span></div>
        <h4 style="color:#ff9800; margin:12px 0 6px;">Memória Recente</h4>
        <ul class="modal-memory">${(state.recent_memory??[]).map(m=>`<li>${typeof m === 'object' ? (m.thought||m.action||JSON.stringify(m)) : m}</li>`).join('')||'<li style="color:#666">Vazia</li>'}</ul>
    `;

    modal.classList.remove('hidden');
}

function closeAgentModal() {
    document.getElementById('agent-modal').classList.add('hidden');
}

// ─── Timeline de Eventos ──────────────────────────────────────────────────────

function addEventToTimeline(events, tick) {
    if (!events || events.length === 0) return;
    const list = document.getElementById('event-list');
    if (!list) return;

    events.forEach(ev => {
        const msg = ev.event_msg || ev.speak || (ev.action ? `[${ev.action}] ${ev.name||''}` : null);
        if (!msg) return;

        const li = document.createElement('li');
        li.className = `event-item event-${ev.action || 'info'}`;
        li.textContent = `T${tick ?? '?'} · ${msg}`;
        list.prepend(li);
    });

    // Manter max 60 itens
    while (list.children.length > 60) list.lastChild.remove();
}

// ─── Replay ───────────────────────────────────────────────────────────────────

async function initReplayPanel() {
    try {
        const resp = await fetch(`${BENCHMARK_API_BASE_URL}/sessions?limit=30`);
        const data = await resp.json();
        const sel = document.getElementById('session-select');
        if (!sel) return;
        sel.innerHTML = '<option value="">-- Selecionar sessão --</option>';
        (data.sessions || []).forEach(s => {
            const dt = new Date(s.started_at * 1000).toLocaleString('pt-BR');
            const status = s.status === 'active' ? '🔴' : '✅';
            const winner = s.winner_model ? ` · ${s.winner_model}` : '';
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${status} ${dt}${winner}`;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.warn('Replay panel: sessões indisponíveis', e);
    }
}

async function loadReplay() {
    const sessionId = document.getElementById('session-select').value;
    if (!sessionId) return;

    const statusEl = document.getElementById('replay-status');
    statusEl.textContent = 'Carregando…';

    try {
        const resp = await fetch(`${BENCHMARK_API_BASE_URL}/sessions/${sessionId}/replay`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        replayFrames = data.frames || [];
        replayIndex = 0;

        const slider = document.getElementById('replay-slider');
        slider.max = Math.max(0, replayFrames.length - 1);
        slider.value = 0;

        document.getElementById('replay-frame-count').textContent = replayFrames.length;
        document.getElementById('replay-controls').style.display = 'block';
        statusEl.textContent = `${replayFrames.length} frames carregados. Clique em ▶ para iniciar.`;
    } catch (e) {
        statusEl.textContent = `Erro: ${e.message}`;
    }
}

function seekReplay(index) {
    replayIndex = parseInt(index, 10);
    applyReplayFrame(replayIndex);
}

function startReplay() {
    if (replayFrames.length === 0) return;
    clearInterval(replayInterval);
    replayInterval = setInterval(() => {
        if (replayIndex >= replayFrames.length - 1) {
            clearInterval(replayInterval);
            document.getElementById('replay-status').textContent = 'Replay concluído.';
            return;
        }
        replayIndex++;
        applyReplayFrame(replayIndex);
        document.getElementById('replay-slider').value = replayIndex;
    }, REPLAY_FPS_MS);
}

function pauseReplay() {
    clearInterval(replayInterval);
}

function stopReplay() {
    clearInterval(replayInterval);
    replayIndex = 0;
    document.getElementById('replay-slider').value = 0;
    applyReplayFrame(0);
}

function applyReplayFrame(index) {
    const frame = replayFrames[index];
    if (!frame) return;
    document.getElementById('replay-tick-label').textContent = `Tick: ${frame.tick}`;

    // Atualizar HUD de benchmark com dados do frame
    if (frame.state && frame.state.agents) {
        updateBenchmarkHUD(frame.state.agents, null);
    }

    // Chamar função de render do main.js se disponível
    if (typeof renderWorldStateReplay === 'function') {
        renderWorldStateReplay(frame.state, frame.tick);
    }
}

// ─── Init ─────────────────────────────────────────────────────────────────────

// Inicializa o painel de replay quando a página carregar
window.addEventListener('DOMContentLoaded', () => {
    setTimeout(initReplayPanel, 2000); // espera 2s para o backend subir
    initBenchmarkDrag();
    restoreBenchmarkPosition();
});

// Fechar modal com ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeAgentModal();
});

// ─── Drag & Drop do Benchmark HUD ────────────────────────────────────────────

function initBenchmarkDrag() {
    const hud    = document.getElementById('benchmark-hud');
    const handle = document.getElementById('benchmark-drag-handle');
    if (!hud || !handle) return;

    // Garantir pointer-events na alça
    hud.style.pointerEvents = 'auto';

    let isDragging = false;
    let startX = 0, startY = 0;
    let origLeft = 0, origTop = 0;

    handle.addEventListener('mousedown', (e) => {
        // Ignorar clique no botão de colapso
        if (e.target.classList.contains('bm-collapse-btn')) return;

        e.preventDefault();
        isDragging = true;

        const rect = hud.getBoundingClientRect();
        // Converter para posição left/top se estiver usando right/bottom
        hud.style.right  = 'auto';
        hud.style.bottom = 'auto';
        hud.style.left   = rect.left + 'px';
        hud.style.top    = rect.top  + 'px';
        hud.style.borderRadius = '8px';

        origLeft = rect.left;
        origTop  = rect.top;
        startX   = e.clientX;
        startY   = e.clientY;

        hud.classList.add('dragging');
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        let newLeft = origLeft + dx;
        let newTop  = origTop  + dy;

        // Manter dentro da tela
        const maxLeft = window.innerWidth  - hud.offsetWidth;
        const maxTop  = window.innerHeight - hud.offsetHeight;
        newLeft = Math.max(0, Math.min(newLeft, maxLeft));
        newTop  = Math.max(0, Math.min(newTop,  maxTop));

        hud.style.left = newLeft + 'px';
        hud.style.top  = newTop  + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (!isDragging) return;
        isDragging = false;
        hud.classList.remove('dragging');
        // Salvar posição
        localStorage.setItem('bm_hud_left', hud.style.left);
        localStorage.setItem('bm_hud_top',  hud.style.top);
    });

    // Touch support (mobile)
    handle.addEventListener('touchstart', (e) => {
        if (e.target.classList.contains('bm-collapse-btn')) return;
        const touch = e.touches[0];
        const rect  = hud.getBoundingClientRect();
        hud.style.right = 'auto'; hud.style.left = rect.left + 'px';
        hud.style.bottom = 'auto'; hud.style.top = rect.top + 'px';
        hud.style.borderRadius = '8px';
        origLeft = rect.left; origTop = rect.top;
        startX = touch.clientX; startY = touch.clientY;
        isDragging = true;
    }, { passive: true });

    document.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const touch = e.touches[0];
        hud.style.left = (origLeft + touch.clientX - startX) + 'px';
        hud.style.top  = (origTop  + touch.clientY - startY) + 'px';
    }, { passive: true });

    document.addEventListener('touchend', () => { isDragging = false; });
}

function restoreBenchmarkPosition() {
    const hud  = document.getElementById('benchmark-hud');
    const left = localStorage.getItem('bm_hud_left');
    const top  = localStorage.getItem('bm_hud_top');
    if (hud && left && top) {
        hud.style.right  = 'auto';
        hud.style.left   = left;
        hud.style.top    = top;
        hud.style.borderRadius = '8px';
    }
}

// ─── Colapsar / Expandir ──────────────────────────────────────────────────────

function toggleBenchmarkCollapse() {
    const body = document.getElementById('benchmark-hud-body');
    const btn  = document.querySelector('.bm-collapse-btn');
    if (!body) return;

    const isCollapsed = body.style.display === 'none';
    body.style.display  = isCollapsed ? '' : 'none';
    if (btn) btn.textContent = isCollapsed ? '▾' : '▸';
}
