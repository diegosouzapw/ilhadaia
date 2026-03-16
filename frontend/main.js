// BBB IA - Frontend 3D Engine
const WORLD_SIZE = 20;
const TILE_SIZE = 2; // Size of each grid block in 3D units

// Scene Setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x87CEEB); // Sky
scene.fog = new THREE.Fog(0x87CEEB, 20, 80);

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
// Start high up looking down (God View)
camera.position.set(WORLD_SIZE, 30, WORLD_SIZE + 10);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
document.getElementById('canvas-container').appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.target.set(WORLD_SIZE, 0, WORLD_SIZE); // Look at center

// Lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(20, 40, 20);
dirLight.castShadow = true;
// Enhance shadow quality
dirLight.shadow.mapSize.width = 2048;
dirLight.shadow.mapSize.height = 2048;
dirLight.shadow.camera.left = -30;
dirLight.shadow.camera.right = 30;
dirLight.shadow.camera.top = 30;
dirLight.shadow.camera.bottom = -30;
scene.add(dirLight);

// Materials
const matGrass = new THREE.MeshLambertMaterial({ color: 0x55aa55 });
const matWater = new THREE.MeshPhongMaterial({ color: 0x44aaff, transparent: true, opacity: 0.8, shininess: 100 });
const matWood = new THREE.MeshLambertMaterial({ color: 0x8B4513 });
const matLeaves = new THREE.MeshLambertMaterial({ color: 0x228B22 });
const matStone = new THREE.MeshLambertMaterial({ color: 0x888888 });
const matGrave = new THREE.MeshLambertMaterial({ color: 0xcccccc });
const matGold = new THREE.MeshPhongMaterial({ color: 0xFFD700, shininess: 100 });

const agentColors = [0xff0000, 0x0000ff, 0xffff00, 0xff00ff];
let agentColorIndex = 0;

// World state
let meshes = {}; // id -> Group/Mesh
let chatHistory = JSON.parse(localStorage.getItem('bbb_chat_history') || '[]');
let chatFilter = "all";
let globalVolume = parseFloat(localStorage.getItem('bbb_volume') || '0.5');
let currentDayCycle = 0; // 0-119, updated from server
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();

// Day/Night color targets
const DAY_SKY = new THREE.Color(0x87CEEB);
const NIGHT_SKY = new THREE.Color(0x1a1a3e);
const DAY_FOG = new THREE.Color(0x87CEEB);
const NIGHT_FOG = new THREE.Color(0x1a1a3e);

// Update UI to match loaded volume
document.getElementById('volume-slider').value = globalVolume;

// --- Sound System ---
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

// --- Configuração de URLs Dinâmicas ---
// Arquivo local (file://) usa 8001. Frontend servido em :3000 usa backend em :8000.
const isFileProtocol = window.location.protocol === 'file:';
const backendPortOverride =
    new URLSearchParams(window.location.search).get('backend_port') ||
    localStorage.getItem('bbb_backend_port');
const BACKEND_PORT = backendPortOverride
    ? String(backendPortOverride)
    : (isFileProtocol ? '8001' : (window.location.port === '3000' ? '8000' : (window.location.port || '8000')));
const BACKEND_HOST = window.location.hostname || 'localhost';

const API_BASE_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const WS_URL = `ws://${BACKEND_HOST}:${BACKEND_PORT}/ws`;

// Token de administrador apenas em memória (não persistido para segurança)
let adminToken = 'dev_token_123';

function setAdminToken(token) {
    adminToken = token;
    console.log("Admin Token atualizado na sessão.");
}

async function updateTickInterval(val) {
    try {
        await fetch(`${API_BASE_URL}/settings/ai_interval?interval=${val}`, { 
            method: 'POST',
            headers: { 'X-Admin-Token': adminToken }
        });
        console.log("AI Interval updated to:", val);
    } catch (e) {
        console.error("Failed to update AI interval", e);
    }
}

// AI Settings Modal Logic
const settingsToggle = document.getElementById('settings-toggle');
const settingsModal = document.getElementById('settings-modal');
const omniFields = document.getElementById('omni-fields');

function normalizeProvider(provider) {
    return 'omnirouter';
}

async function fetchAISettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/settings/ai`);
        const data = await response.json();

        const provider = normalizeProvider(data.ai_provider);
        document.getElementById('ai-provider').value = provider;
        document.getElementById('omniroute-url').value = data.omniroute_url || '';
        document.getElementById('admin-token').value = '';

        updateHeaderInfo(provider, data.ai_model);
        await fetchModels(provider, data.ai_model);
        toggleOmniFields(provider, true);
    } catch (e) {
        console.error("Failed to fetch AI settings", e);
    }
}

async function fetchModels(provider, selectedModelId = null) {
    const normalizedProvider = normalizeProvider(provider);
    const modelSelector = document.getElementById('ai-model');
    const urlInput = document.getElementById('omniroute-url');
    if (!modelSelector) return;

    let urlParam = "";
    if (normalizedProvider === 'omnirouter' && urlInput && urlInput.value) {
        urlParam = `&url=${encodeURIComponent(urlInput.value)}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/models?provider=${normalizedProvider}${urlParam}`);
        const data = await response.json();

        console.log(`Fetched ${data.models ? data.models.length : 0} models for ${normalizedProvider}`);

        modelSelector.innerHTML = "";
        if (data.models && data.models.length > 0) {
            data.models.forEach((m) => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.innerText = m.name;
                if (selectedModelId && m.id === selectedModelId) opt.selected = true;
                modelSelector.appendChild(opt);
            });
        } else {
            const opt = document.createElement('option');
            opt.value = "default";
            opt.innerText = "Padrão do Provedor";
            modelSelector.appendChild(opt);
        }
    } catch (e) {
        console.error("Failed to fetch models", e);
        modelSelector.innerHTML = '<option value="default">Erro ao carregar modelos</option>';
    }
}

function toggleOmniFields(provider, skipFetch = false) {
    const normalizedProvider = normalizeProvider(provider);
    omniFields.style.display = normalizedProvider === 'omnirouter' ? 'block' : 'none';
    if (!skipFetch) {
        fetchModels(normalizedProvider);
    }
}

function updateHeaderInfo(provider, model) {
    const pEl = document.getElementById('display-provider');
    const mEl = document.getElementById('display-model');
    if (pEl) pEl.innerText = 'OMNIROUTER / OPENAI-COMPATIBLE';
    if (mEl) mEl.innerText = model;
}

// Add live update when URL changes
const urlInput = document.getElementById('omniroute-url');
if (urlInput) {
    urlInput.oninput = () => {
        const provider = normalizeProvider(document.getElementById('ai-provider').value);
        if (provider === 'omnirouter') {
            fetchModels(provider);
        }
    };
}

function openSettings() {
    clearSettingsMessage();
    fetchAISettings();
    settingsModal.style.display = 'flex';
}

function closeSettings() {
    settingsModal.style.display = 'none';
}

function showSettingsMessage(text, type) {
    const msgEl = document.getElementById('settings-message');
    if (!msgEl) return;
    msgEl.innerText = text;
    msgEl.className = type; // 'error' or 'success'
}

function clearSettingsMessage() {
    const msgEl = document.getElementById('settings-message');
    if (msgEl) {
        msgEl.innerText = "";
        msgEl.className = "";
    }
}

if (settingsToggle) {
    settingsToggle.onclick = openSettings;
}

async function saveSettings() {
    clearSettingsMessage();
    const ai_provider = normalizeProvider(document.getElementById('ai-provider').value);
    const ai_model = document.getElementById('ai-model').value;
    const omniroute_url = document.getElementById('omniroute-url').value;
    const new_token = document.getElementById('admin-token').value.trim() || adminToken;

    if (!new_token) {
        showSettingsMessage("O TOKEN É OBRIGATÓRIO!", "error");
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/settings/ai`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Token': new_token
            },
            body: JSON.stringify({ ai_provider, ai_model, omniroute_url })
        });
        if (response.ok) {
            const data = await response.json();
            console.log("AI Settings saved successfully");
            setAdminToken(new_token);
            updateHeaderInfo(data.ai_provider, data.ai_model);
            showSettingsMessage("PRESET SALVO!", "success");
            setTimeout(closeSettings, 1000);
        } else {
            console.error("Save failed:", response.status);
            if (response.status === 401) {
                showSettingsMessage("TOKEN INVÁLIDO!", "error");
            } else {
                showSettingsMessage("ERRO NO SERVIDOR!", "error");
            }
        }
    } catch (e) {
        console.error("Error saving AI settings", e);
        showSettingsMessage("ERRO DE CONEXÃO!", "error");
    }
}

async function toggleFastMode(isFast) {
    const dropdown = document.getElementById('tick-interval-selector');
    try {
        if (isFast) {
            // Parallel mode: interval = 0
            if (dropdown) dropdown.disabled = true;
            await fetch(`${API_BASE_URL}/settings/ai_interval?interval=0`, { 
                method: 'POST',
                headers: { 'X-Admin-Token': adminToken }
            });
        } else {
            // Restore turn-based mode from dropdown value
            const val = dropdown ? dropdown.value : 5;
            if (dropdown) dropdown.disabled = false;
            await fetch(`${API_BASE_URL}/settings/ai_interval?interval=${val}`, { 
                method: 'POST',
                headers: { 'X-Admin-Token': adminToken }
            });
        }
        console.log("Fast mode set to:", isFast);
    } catch (e) {
        console.error("Failed to update Fast Mode", e);
    }
}

function playSynthSound(type) {
    if (audioCtx.state === 'suspended') audioCtx.resume();
    
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    const now = audioCtx.currentTime;
    
    // Base gains adjusted by globalVolume
    const vol = globalVolume;
    
    if (type === 'walk') {
        oscillator.type = 'sine';
        oscillator.frequency.setValueAtTime(120, now);
        oscillator.frequency.exponentialRampToValueAtTime(10, now + 0.1);
        gainNode.gain.setValueAtTime(0.02 * vol, now);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
        oscillator.start(now);
        oscillator.stop(now + 0.1);
    } else if (type === 'pick') {
        oscillator.type = 'triangle';
        oscillator.frequency.setValueAtTime(440, now);
        oscillator.frequency.exponentialRampToValueAtTime(880, now + 0.15);
        gainNode.gain.setValueAtTime(0.1 * vol, now);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.2);
        oscillator.start(now);
        oscillator.stop(now + 0.2);
    } else if (type === 'eat' || type === 'drink') {
        oscillator.type = 'square';
        oscillator.frequency.setValueAtTime(200, now);
        oscillator.frequency.exponentialRampToValueAtTime(60, now + 0.25);
        gainNode.gain.setValueAtTime(0.05 * vol, now);
        gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
        oscillator.start(now);
        oscillator.stop(now + 0.3);
    }
}

// --- Build the Island (Base Plane) ---
const islandGeometry = new THREE.BoxGeometry(WORLD_SIZE * TILE_SIZE, 2, WORLD_SIZE * TILE_SIZE);
const island = new THREE.Mesh(islandGeometry, matGrass);
island.position.set(WORLD_SIZE, -1, WORLD_SIZE); // Center the island
island.receiveShadow = true;
scene.add(island);

// Add some water around
const waterGeo = new THREE.PlaneGeometry(WORLD_SIZE * TILE_SIZE * 3, WORLD_SIZE * TILE_SIZE * 3);
const water = new THREE.Mesh(waterGeo, matWater);
water.rotation.x = -Math.PI / 2;
water.position.set(WORLD_SIZE, -0.5, WORLD_SIZE);
scene.add(water);

// Add invisible grid helper overlay for debugging mapping
const gridHelper = new THREE.GridHelper(WORLD_SIZE * TILE_SIZE, WORLD_SIZE);
gridHelper.position.set(WORLD_SIZE, 0.1, WORLD_SIZE);
gridHelper.material.transparent = true;
gridHelper.material.opacity = 0.2;
scene.add(gridHelper);

// --- Entity Creation ---
const matFruit = new THREE.MeshLambertMaterial({ color: 0xff3333 }); // Red fruit

function createTree() {
    const group = new THREE.Group();
    // Trunk (Taller and thicker)
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.4, 2.8), matWood);
    trunk.position.y = 1.4;
    trunk.castShadow = true;
    group.add(trunk);
    
    // Leaves (Bigger)
    const leaves = new THREE.Mesh(new THREE.DodecahedronGeometry(1.8), matLeaves);
    leaves.position.y = 3.2;
    leaves.castShadow = true;
    group.add(leaves);
    
    // Fruit group
    const fruits = new THREE.Group();
    
    // Add 3 fruits around the leaves
    const f1 = new THREE.Mesh(new THREE.SphereGeometry(0.35), matFruit);
    f1.position.set(1.4, 3.2, 0);
    const f2 = new THREE.Mesh(new THREE.SphereGeometry(0.35), matFruit);
    f2.position.set(-1.0, 2.8, 1.2);
    const f3 = new THREE.Mesh(new THREE.SphereGeometry(0.35), matFruit);
    f3.position.set(0, 3.6, -1.5);
    
    fruits.add(f1, f2, f3);
    group.add(fruits);
    
    group.userData = { fruitsGroup: fruits };
    
    return group;
}

function createStone() {
    const geo = new THREE.DodecahedronGeometry(0.8, 1);
    const mesh = new THREE.Mesh(geo, matStone);
    mesh.position.y = 0.4;
    mesh.castShadow = true;
    return mesh;
}

function createPondTile() {
    const geo = new THREE.BoxGeometry(TILE_SIZE, 0.2, TILE_SIZE);
    const mesh = new THREE.Mesh(geo, matWater);
    mesh.position.y = -0.1;
    return mesh;
}

function createCross() {
    const group = new THREE.Group();
    const crossBar1 = new THREE.Mesh(new THREE.BoxGeometry(0.2, 1.2, 0.2), matStone);
    crossBar1.position.y = 0.6;
    crossBar1.castShadow = true;
    group.add(crossBar1);
    
    const crossBar2 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.2, 0.2), matStone);
    crossBar2.position.y = 0.9;
    crossBar2.castShadow = true;
    group.add(crossBar2);
    
    return group;
}

function createHouse(name, color = 0xffffff, rotationY = 0) {
    const group = new THREE.Group();
    // Base
    const base = new THREE.Mesh(new THREE.BoxGeometry(2.5, 2.5, 2.5), new THREE.MeshLambertMaterial({ color: 0x8D6E63 })); // Wood color
    base.position.y = 1.25;
    base.castShadow = true;
    base.receiveShadow = true;
    group.add(base);
    // Roof
    const roofGeo = new THREE.ConeGeometry(2.2, 1.8, 4);
    const roof = new THREE.Mesh(roofGeo, new THREE.MeshLambertMaterial({ color: color }));
    roof.position.y = 3.4;
    roof.rotation.y = Math.PI / 4;
    roof.castShadow = true;
    group.add(roof);
    // Door
    const doorGroup = new THREE.Group();
    const door = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.4, 0.1), new THREE.MeshLambertMaterial({ color: 0x3E2723 }));
    door.position.set(0, 0.7, 1.25);
    doorGroup.add(door);
    doorGroup.rotation.y = rotationY;
    group.add(doorGroup);

    // --- 3D SIGNBOARD (Like Cemetery) ---
    const signGroup = new THREE.Group();
    // Pole
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.8), matWood);
    pole.position.set(-0.7, 0.4, 1.25);
    signGroup.add(pole);
    // Board
    const board = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.4, 0.05), matWood);
    board.position.set(-0.7, 0.65, 1.25);
    signGroup.add(board);
    
    signGroup.rotation.y = rotationY;
    group.add(signGroup);

    // HTML Name label logic for house (using the same element)
    const nameLabel = document.createElement('div');
    nameLabel.className = 'name-label';
    nameLabel.innerText = name;
    nameLabel.style.backgroundColor = 'rgba(0,0,0,0.8)'; // Darker for houses
    nameLabel.style.border = '1px solid #ffeb3b';
    document.getElementById('bubbles-layer').appendChild(nameLabel);

    group.userData = { 
        type: 'house',
        name: name,
        nameElement: nameLabel
    };

    return group;
}

function createCemeteryArea() {
    const group = new THREE.Group();
    const floor = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.1, 3.5), new THREE.MeshLambertMaterial({ color: 0x212121 }));
    floor.position.y = 0.05;
    floor.receiveShadow = true;
    group.add(floor);
    // Sign
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.2), matWood);
    pole.position.set(1.4, 0.6, 1.4);
    group.add(pole);
    const sign = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.5, 0.1), matWood);
    sign.position.set(1.4, 0.9, 1.4);
    group.add(sign);
    return group;
}

function createTrophy() {
    const group = new THREE.Group();
    const base = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.2, 0.5), matStone);
    group.add(base);
    
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.8), matGold);
    stem.position.y = 0.5;
    group.add(stem);
    
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.2, 0.5), matGold);
    cup.position.y = 1.0;
    group.add(cup);
    
    group.position.y = 2.5; // High above head
    return group;
}

function createAgent(name) {
    const group = new THREE.Group();
    
    // Pick color
    const color = agentColors[agentColorIndex % agentColors.length];
    agentColorIndex++;
    
    const matBody = new THREE.MeshLambertMaterial({ color: color });
    
    // Legs
    const legGeo = new THREE.BoxGeometry(0.35, 0.6, 0.35);
    legGeo.translate(0, -0.3, 0); // Translate center to the top (hip joint)
    const legL = new THREE.Mesh(legGeo, matBody);
    legL.position.set(-0.25, 0.6, 0);
    legL.castShadow = true;
    group.add(legL);

    const legR = new THREE.Mesh(legGeo, matBody);
    legR.position.set(0.25, 0.6, 0);
    legR.castShadow = true;
    group.add(legR);

    // Body (Minecraft style box)
    const bodyGeo = new THREE.BoxGeometry(0.9, 0.9, 0.5);
    const body = new THREE.Mesh(bodyGeo, matBody);
    body.position.y = 1.05;
    body.castShadow = true;
    group.add(body);
    
    // Arms
    const armGeo = new THREE.BoxGeometry(0.25, 0.8, 0.25);
    armGeo.translate(0, -0.4, 0); // Translate center to the top (shoulder joint)
    const armL = new THREE.Mesh(armGeo, matBody);
    armL.position.set(-0.6, 1.5, 0);
    armL.castShadow = true;
    group.add(armL);

    const armR = new THREE.Mesh(armGeo, matBody);
    armR.position.set(0.6, 1.5, 0);
    armR.castShadow = true;
    group.add(armR);
    
    // Head -> to attach bubbles later
    const headGeo = new THREE.BoxGeometry(0.7, 0.7, 0.7);
    // Lighter color for head
    const matHead = new THREE.MeshLambertMaterial({ color: 0xffccaa });
    const head = new THREE.Mesh(headGeo, matHead);
    head.position.y = 1.85;
    head.castShadow = true;
    group.add(head);

    // Eyes (to know where they are looking)
    const eyeGeo = new THREE.BoxGeometry(0.1, 0.1, 0.1);
    const matEye = new THREE.MeshLambertMaterial({ color: 0x000000 });
    const eyeL = new THREE.Mesh(eyeGeo, matEye);
    eyeL.position.set(-0.15, 1.95, 0.36); // front of head is +Z
    group.add(eyeL);
    
    const eyeR = new THREE.Mesh(eyeGeo, matEye);
    eyeR.position.set(0.15, 1.95, 0.36);
    group.add(eyeR);
    
    // Held item (small fruit in hand)
    const heldItemGeo = new THREE.SphereGeometry(0.2);
    // Reuse matFruit defined earlier
    const heldItem = new THREE.Mesh(heldItemGeo, matFruit);
    heldItem.position.set(0.6, 0.6, 0.3); // Right hand position, lower
    heldItem.castShadow = true;
    heldItem.visible = false; // Hidden by default
    group.add(heldItem);
    
    // Vision Cone (Campo de Visão)
    // O cone baseia-se na altura de 6 e raio da base de 4
    const coneGeo = new THREE.ConeGeometry(5, 7, 16);
    coneGeo.translate(0, -3.5, 0); // Desloca para o topo rotacionar a partir do olho
    coneGeo.rotateX(-Math.PI / 2); // Deita o cone apontando pro +Z
    const matCone = new THREE.MeshBasicMaterial({ color: 0xffff00, transparent: true, opacity: 0.15, depthWrite: false });
    const visionCone = new THREE.Mesh(coneGeo, matCone);
    visionCone.position.set(0, 1.95, 0.4); // Colado nos olhos
    group.add(visionCone);
    
    // HTML Bubble logic
    const bubble = document.createElement('div');
    bubble.className = 'speech-bubble';
    document.getElementById('bubbles-layer').appendChild(bubble);
    
    // HTML Name label logic
    const nameLabel = document.createElement('div');
    nameLabel.className = 'name-label';
    nameLabel.innerText = name;
    document.getElementById('bubbles-layer').appendChild(nameLabel);
    
    group.userData = { 
        name: name, 
        bubbleElement: bubble, 
        nameElement: nameLabel, 
        speakingTime: 0,
        heldItemMesh: heldItem,
        trophyMesh: null,
        walkCounter: 0,
        legL: legL,
        legR: legR,
        armL: armL,
        armR: armR
    };
    return group;
}

function createDroppedFruit() {
    const geo = new THREE.SphereGeometry(0.25);
    const mesh = new THREE.Mesh(geo, matFruit);
    mesh.position.y = 0.25; // Floor level
    mesh.castShadow = true;
    return mesh;
}

// Convert Grid X,Y to World Position
function gridToWorld(x, y) {
    // Top-left is 0,0. Center of tile.
    return {
        x: x * TILE_SIZE + (TILE_SIZE / 2),
        z: y * TILE_SIZE + (TILE_SIZE / 2)
    };
}

// --- WebSocket Connection ---
const wsStatus = document.getElementById("ws-status");
let socket;
let nextTickTime = Date.now() + 5000;

function connectWebSocket() {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        wsStatus.textContent = "Conectado";
        wsStatus.className = "connected";
    };

    socket.onclose = () => {
        wsStatus.textContent = "Desconectado - Reconectando...";
        wsStatus.className = "disconnected";
        // Tenta reconectar em 2 segundos
        setTimeout(connectWebSocket, 2000);
    };

    socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        if (message.type === "init" || message.type === "update" || message.type === "reset") {
            // Se for um reset oficial ou o servidor acabou de ligar (ticks baixos), limpa o chat
            if (message.type === "reset" || (message.type === "init" && message.data.ticks <= 1)) {
                chatHistory = [];
                localStorage.removeItem('bbb_chat_history');
                renderChat();
                // Hide extra filter buttons
                ["filter-joao", "filter-maria", "filter-zeca", "filter-elly"].forEach(id => {
                    const btn = document.getElementById(id);
                    if (btn) btn.style.display = "none";
                });
            }

            if (message.type === "init") {
                // Restore settings from backend on first load if available
                if (message.data.ai_interval !== undefined) {
                    const selector = document.getElementById("tick-interval-selector");
                    if (selector) selector.value = message.data.ai_interval;

                    const fastModeCheckbox = document.getElementById("fast-mode-checkbox");
                    if (fastModeCheckbox) fastModeCheckbox.checked = (message.data.ai_interval === 0);
                }
                if (message.data.player_count) {
                    const selector = document.getElementById("player-count-selector");
                    if (selector) selector.value = message.data.player_count;
                }
            }
            
            updateWorld(message.data);
            
            if (message.events) {
                handleEvents(message.events);
                // T16: Timeline de eventos
                if (typeof addEventToTimeline === 'function') {
                    addEventToTimeline(message.events, message.data?.ticks);
                }
            }

            // T16: HUD de Benchmark — atualiza com agentes do estado
            if (typeof updateBenchmarkHUD === 'function' && message.data?.agents) {
                updateBenchmarkHUD(message.data.agents, message.data?.session_id);
            }
        }
    };
}

// Inicia a primeira conexão
connectWebSocket();
renderChat();

// --- World Sync Logic ---
function updateWorld(data) {
    if (!data.game_over) {
        document.getElementById("tick-counter").textContent = data.ticks;
    }
    // Update day/night cycle
    if (data.day_cycle !== undefined) {
        currentDayCycle = data.day_cycle;
        
        // Calculate 24h clock: 1 tick = 12 minutes. 
        // 0 ticks = 04:00 AM (Sunrise cycle starts with dawn at 110-120 and 0-10)
        let totalMinutes = (data.day_cycle * 12) + (4 * 60); 
        let hours = Math.floor(totalMinutes / 60) % 24;
        let minutes = totalMinutes % 60;
        let timeStr = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
        const clockEl = document.getElementById("game-clock");
        if (clockEl) clockEl.textContent = timeStr;

        const icon = document.getElementById("day-night-icon");
        if (icon) {
            if (data.is_night) {
                icon.textContent = "🌙 Noite";
            } else if (data.day_cycle >= 70) {
                icon.textContent = "🌅 Entardecer";
            } else if (data.day_cycle >= 110 || data.day_cycle < 10) {
                icon.textContent = "🌄 Amanhecer";
            } else {
                icon.textContent = "☀️ Dia";
            }
        }
    }
    if (data.next_agent) {
        document.getElementById("next-agent").textContent = data.next_agent;
    }
    if (data.ticks_to_next_turn !== undefined) {
         nextTickTime = Date.now() + (data.ticks_to_next_turn * 1000);
         
         // Ensure dropdown matches backend state (if it changed elsewhere)
         const selector = document.getElementById("tick-interval-selector");
         const fastModeCheckbox = document.getElementById("fast-mode-checkbox");
         const isFastMode = data.ai_interval === 0;
         
         if (fastModeCheckbox && data.ai_interval !== undefined) {
             fastModeCheckbox.checked = isFastMode;
         }
         if (selector && data.ai_interval !== undefined) {
             selector.disabled = isFastMode;
             if (!isFastMode && selector.value != data.ai_interval) {
                 selector.value = data.ai_interval;
             }
         }

         const playerSelector = document.getElementById("player-count-selector");
         if (playerSelector && data.player_count && playerSelector.value != data.player_count) {
             playerSelector.value = data.player_count;
         }
         
         // Update Victory UI
         const overlay = document.getElementById("victory-overlay");
         if (data.game_over) {
             overlay.classList.remove("hidden");
             const winner = data.entities[data.winner_id];
             const titleEl = document.getElementById("victory-title");
             const contentEl = document.querySelector(".victory-content");
             
             if (winner) {
                 titleEl.innerText = "🏆 VENCEDOR! 🏆";
                 contentEl.style.background = "linear-gradient(135deg, #FFD700, #FFA500)";
                 document.getElementById("winner-name").innerText = winner.name;
                 document.querySelectorAll(".winner-stats").forEach(el => el.style.display = "flex");
                 document.getElementById("win-hp").innerText = winner.hp;
                 document.getElementById("win-fome").innerText = winner.hunger;
                 document.getElementById("win-sede").innerText = winner.thirst;
                 document.getElementById("win-friendship").innerText = winner.friendship || 0;
                 
                 // Add 3D Trophy if not present
                 if (meshes[data.winner_id] && !meshes[data.winner_id].userData.trophyMesh) {
                     const trophy = createTrophy();
                     meshes[data.winner_id].add(trophy);
                     meshes[data.winner_id].userData.trophyMesh = trophy;
                 }
             } else {
                 titleEl.innerText = "💀 GAME OVER! 💀";
                 contentEl.style.background = "linear-gradient(135deg, #444, #111)";
                 contentEl.style.color = "white";
                 document.getElementById("winner-name").innerText = "SEM SOBREVIVENTES";
                 document.querySelectorAll(".winner-stats").forEach(el => el.style.display = "none");
             }
             
             // Update reset countdown
             const nextReset = data.reset_countdown;
             const timerBox = document.getElementById("reset-countdown-text");
             const timerSec = document.getElementById("reset-timer");
             if (nextReset !== null && nextReset !== undefined) {
                 if (timerBox) timerBox.style.display = "block";
                 if (timerSec) timerSec.innerText = nextReset;
             } else {
                 if (timerBox) timerBox.style.display = "none";
             }
         } else {
             overlay.classList.add("hidden");
         }
    }
    
    // Cleanup removed entities (handles backend reloads or item drops/consumes)
    for (const id in meshes) {
        if (!data.entities[id]) {
            const mesh = meshes[id];
            scene.remove(mesh);
            if (mesh.userData && mesh.userData.nameElement && mesh.userData.nameElement.parentNode) {
                mesh.userData.nameElement.parentNode.removeChild(mesh.userData.nameElement);
            }
            if (mesh.userData && mesh.userData.bubbleElement && mesh.userData.bubbleElement.parentNode) {
                mesh.userData.bubbleElement.parentNode.removeChild(mesh.userData.bubbleElement);
            }
            delete meshes[id];
        }
    }
    
    // Update HTML Agent List stats
    const agentListHTML = [];
    
    for (const id in data.entities) {
        const entity = data.entities[id];
        const pos = gridToWorld(entity.x, entity.y);
        
        if (!meshes[id]) {
            // Create new entity
            let mesh;
            if (entity.type === "tree") mesh = createTree();
            else if (entity.type === "stone") mesh = createStone();
            else if (entity.type === "agent") {
                mesh = createAgent(entity.name);
                // Update filter buttons visibility
                const filterId = `filter-${entity.name.toLowerCase()}`;
                const filterBtn = document.getElementById(filterId);
                if (filterBtn) filterBtn.style.display = "block";
            }
            else if (entity.type === "dead_agent") mesh = createCross();
            else if (entity.type === "dropped_fruit" || entity.type === "fruit") mesh = createDroppedFruit();
            else if (entity.type === "water") mesh = createPondTile();
            else if (entity.type === "house") {
                let houseColor = 0xffffff;
                let rotation = 0;
                
                if (entity.name.includes("João")) {
                    houseColor = 0x2196F3; // Blue
                    rotation = 0; // Faces +Z (Down)
                } else if (entity.name.includes("Maria")) {
                    houseColor = 0xF44336; // Red
                    rotation = -Math.PI / 2; // Faces +X (Right)
                } else if (entity.name.includes("Zeca")) {
                    houseColor = 0x4CAF50; // Green
                    rotation = Math.PI; // Faces -Z (Up)
                } else if (entity.name.includes("Elly")) {
                    houseColor = 0x9C27B0; // Purple
                    rotation = Math.PI / 2; // Faces -X (Left)
                }
                mesh = createHouse(entity.name, houseColor, rotation);
            }
            else if (entity.type === "cemetery") mesh = createCemeteryArea();
            
            if (mesh) {
                mesh.position.set(pos.x, 0, pos.z);
                mesh.userData = mesh.userData || {};
                mesh.userData.entityId = id;
                mesh.userData.entityType = entity.type;
                scene.add(mesh);
                meshes[id] = mesh;
            }
        } else {
            // Store target position for smooth interpolation in the animate loop
            meshes[id].userData.targetPos = { x: pos.x, z: pos.z };
        }
        
        // Update tree fruit logic based on fruit stage (1=small, 2=medium, 3=mature)
        if (entity.type === "tree" && meshes[id]) {
            const stage = entity.fruit_stage || 1;
            const scale = stage === 1 ? 0.2 : (stage === 2 ? 0.6 : 1.0);
            meshes[id].userData.fruitsGroup.scale.set(scale, scale, scale);
        }
        
        // Update agent visuals (death, carrying, item, zombie)
        if (entity.type === "agent" && meshes[id]) {
            const mesh = meshes[id];
            
            // ZOMBIE visual: Moss green color, arms forward
            if (entity.is_zombie) {
                mesh.rotation.z = 0;
                mesh.position.y = 0;
                // Change color to moss green if not already
                if (!mesh.userData.isZombified) {
                    mesh.userData.isZombified = true;
                    const zombieColor = 0x556B2F; // Dark olive/moss green
                    const zombieMat = new THREE.MeshLambertMaterial({ color: zombieColor });
                    // Recolor body, legs, arms
                    if (mesh.userData.legL) mesh.userData.legL.material = zombieMat;
                    if (mesh.userData.legR) mesh.userData.legR.material = zombieMat;
                    if (mesh.userData.armL) mesh.userData.armL.material = zombieMat;
                    if (mesh.userData.armR) mesh.userData.armR.material = zombieMat;
                    // Body is child index 2 (after 2 legs)
                    if (mesh.children[2]) mesh.children[2].material = zombieMat;
                    // Head gets a sickly green
                    const zombieHeadMat = new THREE.MeshLambertMaterial({ color: 0x8FBC8F }); // Dark sea green
                    if (mesh.children[5]) mesh.children[5].material = zombieHeadMat; // Head
                }
                // Arms forward (zombie pose) — rotate arms on X axis
                if (mesh.userData.armL) mesh.userData.armL.rotation.x = -Math.PI / 2;
                if (mesh.userData.armR) mesh.userData.armR.rotation.x = -Math.PI / 2;
            }
            // Death visual: Lying down (only if NOT zombie)
            else if (entity.is_alive === false) {
                mesh.rotation.z = Math.PI / 2;
                mesh.position.y = 0.3; // Floor level
            } else {
                mesh.rotation.z = 0;
                mesh.position.y = 0;
                // Reset arms if not zombie
                if (mesh.userData.armL) mesh.userData.armL.rotation.x = 0;
                if (mesh.userData.armR) mesh.userData.armR.rotation.x = 0;
            }

            // Item in hand (like a fruit or a body)
            if (mesh.userData.heldItemMesh) {
                mesh.userData.heldItemMesh.visible = !!entity.held_item;
            }

            // Sync name dynamically (e.g. when becoming a Zombie)
            if (mesh.userData.nameElement && mesh.userData.name !== entity.name) {
                mesh.userData.nameElement.innerText = entity.name;
                mesh.userData.name = entity.name;
            }
        }
        
        // Populate UI Panel for agents
        if (entity.type === "agent") {
            const hpColor = entity.hp > 50 ? 'lightgreen' : (entity.hp > 0 ? 'orange' : 'red');
            const friendshipColor = entity.friendship > 70 ? 'pink' : (entity.friendship > 30 ? 'white' : 'gray');
            const zombieTag = entity.is_zombie ? '🧟' : '';
            agentListHTML.push(`
                <li class="agent-stat" style="${entity.is_zombie ? 'border-left: 3px solid #556B2F; background: rgba(85,107,47,0.3);' : ''}">
                    <span><strong>${entity.name}</strong> ${entity.is_zombie ? '🧟' : (entity.is_alive ? '' : '💀')}</span>
                    <div style="font-size: 0.9em; opacity: 0.9;">
                        HP: <span style="color:${hpColor}">${entity.hp}</span> | 
                        F: <span style="${entity.hunger < 30 ? 'color:orange; font-weight:bold;' : ''}">${entity.hunger}</span> | 
                        S: <span style="${entity.thirst < 30 ? 'color:orange; font-weight:bold;' : ''}">${entity.thirst}</span> | 
                        ❤️: <span style="color:${friendshipColor}">${entity.friendship}</span>
                    </div>
                    <div style="font-size: 0.8em; color: #ccc;">🍎: ${entity.apples_eaten || 0} | 💧: ${entity.water_drunk || 0} | 🗣️: ${entity.chats_sent || 0}</div>
                </li>
            `);
        }
    }
    
    document.getElementById("agent-list").innerHTML = agentListHTML.join("");

    // Update Hall of Fame (Scores)
    if (data.scores) {
        let scoresHTML = "";
        for (const [name, wins] of Object.entries(data.scores)) {
            scoresHTML += `<div style="padding: 2px 0;">🌟 <strong>${name}</strong>: ${wins} Vitórias</div>`;
        }
        document.getElementById("scores-list").innerHTML = scoresHTML || "Nenhuma vitória ainda.";
    }

    // Update Hall of Fame (Life Records)
    if (data.hall_of_fame && data.hall_of_fame.length > 0) {
        let recordsHTML = "";
        data.hall_of_fame.forEach((record, i) => {
            const medal = i === 0 ? "🥇" : (i === 1 ? "🥈" : "🥉");
            recordsHTML += `<div style="padding: 3px 0; border-bottom: 1px solid #333;">${medal} <strong>${record.name}</strong> — 🍎${record.apples} | 💧${record.water} | 🗣️${record.chats} <span style="color: #ffeb3b;">(${record.score} pts)</span></div>`;
        });
        document.getElementById("records-list").innerHTML = recordsHTML;
    } else {
        const recordsEl = document.getElementById("records-list");
        if (recordsEl) recordsEl.innerHTML = "Nenhum recorde ainda.";
    }

    // --- Update Inventory UI ---
    const invContainer = document.getElementById("inventories");
    let invHTML = "";
    
    for (const id in data.entities) {
        const entity = data.entities[id];
        if (entity.type === "agent") {
            const inventory = entity.inventory || [];
            invHTML += `
                <div class="agent-inventory">
                    <h4>Bolsa de ${entity.name}</h4>
                    <div class="inv-slots">
                        ${[0, 1, 2].map(i => {
                            const item = inventory[i];
                            let icon = '';
                            if (item === 'fruit') icon = '🍎';
                            else if (item === 'water_bottle') icon = '🍶';
                            else if (item === 'dead_body') icon = '💀';
                            return `<div class="inv-slot ${item ? 'filled' : ''}">${icon}</div>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }
    }
    invContainer.innerHTML = invHTML;
}

function findAgentRoot(object3d) {
    let current = object3d;
    while (current) {
        if (current.userData && current.userData.entityType === 'agent') {
            return current;
        }
        current = current.parent;
    }
    return null;
}

function handleWorldClick(event) {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);

    const hits = raycaster.intersectObjects(scene.children, true);
    for (const hit of hits) {
        const agentRoot = findAgentRoot(hit.object);
        if (!agentRoot) continue;
        const agentId = agentRoot.userData?.entityId;
        if (agentId && typeof showAgentModal === 'function') {
            showAgentModal(agentId);
        }
        break;
    }
}

// T13/T16: renderer de replay chamado por benchmark.js
function renderWorldStateReplay(state, tickOverride) {
    if (!state) return;
    const replayState = { ...state };
    if (tickOverride !== undefined && tickOverride !== null) {
        replayState.ticks = tickOverride;
    }
    updateWorld(replayState);
}

// Chat Persistence Helpers
function saveChat() {
    localStorage.setItem('bbb_chat_history', JSON.stringify(chatHistory));
}

function setChatFilter(filter) {
    chatFilter = filter;
    // Update buttons
    document.querySelectorAll(".filter-btn").forEach(btn => {
        btn.classList.remove("active");
        if (btn.innerText === filter || (filter === 'all' && btn.innerText === 'Todos')) {
            btn.classList.add("active");
        }
    });
    renderChat();
}

function renderChat() {
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = "";
    chatHistory.forEach(msg => {
        // Global events (Sistema) show in all filters, specific agents only in their filter or 'all'
        if (chatFilter === "all" || msg.isGlobal || msg.agentName === chatFilter) {
            const li = document.createElement('li');
            li.className = 'chat-msg';
            li.innerHTML = msg.html;
            chatMessages.appendChild(li);
        }
    });
    
    const autoscroll = document.getElementById('chat-autoscroll')?.checked;
    if (autoscroll) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function handleEvents(events) {
    for (let i = 0; i < events.length; i++) {
        const ev = events[i];
        
        if (ev.speak && ev.speak.trim() !== '') {
            showSpeechBubble(ev.agent_id, ev.speak);
            
            let nameHeader = `<span class="name">${ev.name}</span>`;
            if (ev.target_name && ev.target_name.trim() !== '') {
                nameHeader = `<span class="name">${ev.name}</span> <span style="font-size: 0.85em; opacity: 0.8; color: #ccc;">para</span> <span class="name">${ev.target_name}</span>`;
            }

            chatHistory.push({
                agentName: ev.name,
                isGlobal: false,
                html: `${nameHeader}: ${ev.speak}`
            });
            saveChat();
        }
        
        if (ev.event_msg) {
            let color = "white";
            const isGlobal = !ev.name;
            const displayName = ev.name || "SISTEMA";

            if (ev.action === "gather" || ev.action === "pick_up") {
                color = "lightgreen";
                playSynthSound('pick');
            }
            if (ev.action === "eat") {
                color = "aqua";
                playSynthSound('eat');
            }
            if (ev.action === "drink") {
                color = "deepskyblue";
                playSynthSound('drink');
            }
            if (ev.action === "die") color = "#ff4d4d"; // Red
            if (ev.action === "victory") color = "gold";
            if (ev.action === "draw") color = "orange-red";
            if (ev.event_msg.includes("miasma")) color = "#ff5722"; // Bright Orange-Red for alert
            if (ev.event_msg.includes("TENTOU") || ev.event_msg.includes("falhou") || ev.event_msg.includes("VAZIA")) color = "orange";

            chatHistory.push({
                agentName: ev.name,
                isGlobal: isGlobal,
                html: `<span class="name" style="color: ${color};">* ${displayName}</span> <span style="color: ${color};">${ev.event_msg}</span>`
            });
            saveChat();
        }
    }
    renderChat();
}

async function resetGame(count) {
    // If count not provided, try to read from dropdown
    const playerCount = count || document.getElementById('player-count-selector')?.value || 4;
    try {
        const response = await fetch(`${API_BASE_URL}/reset?player_count=${playerCount}`, { 
            method: 'POST',
            headers: { 'X-Admin-Token': adminToken }
        });
        if (response.ok) {
            chatHistory = [];
            localStorage.removeItem('bbb_chat_history');
            renderChat();
            // The server will broadcast the reset
        } else if (response.status === 401) {
            alert("Não autorizado. Verifique seu Admin Token no console (setAdminToken('seu_token')).");
        }
    } catch (e) {
        console.error("Reset failed", e);
    }
}

function showSpeechBubble(agentId, text) {
    const mesh = meshes[agentId];
    if (mesh && mesh.userData && mesh.userData.bubbleElement) {
        const bubble = mesh.userData.bubbleElement;
        bubble.innerText = text;
        bubble.style.opacity = 1;
        mesh.userData.speakingTime = 150; // frames to show
    }
}

// --- Render Loop ---
function animate() {
    requestAnimationFrame(animate);
    
    controls.update();
    
    // Update HTML Speech Bubbles and Names to follow 3D Heads
    for (const id in meshes) {
        const mesh = meshes[id];
        
        // --- Smooth Movement Interpolation ---
        if (mesh.userData.targetPos) {
            const tPos = mesh.userData.targetPos;
            const dx = tPos.x - mesh.position.x;
            const dz = tPos.z - mesh.position.z;
            
            // Move toward target at constant speed (1 tile per second at ~60fps)
            const dist = Math.sqrt(dx * dx + dz * dz);
            const moveSpeed = TILE_SIZE / 60;
            if (dist > moveSpeed) {
                mesh.position.x += (dx / dist) * moveSpeed;
                mesh.position.z += (dz / dist) * moveSpeed;
                
                // Rotate to face direction
                const targetRotation = Math.atan2(dx, dz);
                mesh.rotation.y += (targetRotation - mesh.rotation.y) * 0.1;

                // Animate limbs
                if (mesh.userData.legL && mesh.userData.legR) {
                    const walkCycle = Math.sin(mesh.userData.walkCounter * 0.25);
                    mesh.userData.legL.rotation.x = walkCycle * 0.5;
                    mesh.userData.legR.rotation.x = -walkCycle * 0.5;
                    mesh.userData.armL.rotation.x = -walkCycle * 0.5;
                    mesh.userData.armR.rotation.x = walkCycle * 0.5;
                }

                // Play walk sound periodically
                if (mesh.userData.walkCounter % 20 === 0) {
                    playSynthSound('walk');
                }
                mesh.userData.walkCounter++;
            } else {
                mesh.position.x = tPos.x;
                mesh.position.z = tPos.z;
                mesh.userData.walkCounter = 0;
                
                // Reset limbs
                if (mesh.userData.legL) {
                    mesh.userData.legL.rotation.x = 0;
                    mesh.userData.legR.rotation.x = 0;
                    mesh.userData.armL.rotation.x = 0;
                    mesh.userData.armR.rotation.x = 0;
                }
            }
        }

        if (mesh.userData && mesh.userData.nameElement) {
            
            // 1. Atualiza Posição do Nome
            const vecName = new THREE.Vector3();
            vecName.setFromMatrixPosition(mesh.matrixWorld);
            
            // Offset na altura dependendo do tipo
            const heightOffset = (mesh.userData.type === 'house') ? 4.5 : 2.6;
            vecName.y += heightOffset; 
            
            vecName.project(camera);
            
            const xName = (vecName.x * .5 + .5) * window.innerWidth;
            const yName = (vecName.y * -.5 + .5) * window.innerHeight;
            
            mesh.userData.nameElement.style.left = `${xName}px`;
            mesh.userData.nameElement.style.top = `${yName}px`;
            
            // 2. Atualiza Posição do Balão (Fica um pouco mais acima do nome)
            if (mesh.userData.bubbleElement) {
                if (mesh.userData.speakingTime > 0) {
                    mesh.userData.speakingTime--;
                    
                    const vecBubble = new THREE.Vector3();
                    vecBubble.setFromMatrixPosition(mesh.matrixWorld);
                    vecBubble.y += 3.4; 
                    vecBubble.project(camera);
                    
                    const xBubble = (vecBubble.x * .5 + .5) * window.innerWidth;
                    const yBubble = (vecBubble.y * -.5 + .5) * window.innerHeight;
                    
                    mesh.userData.bubbleElement.style.left = `${xBubble}px`;
                    mesh.userData.bubbleElement.style.top = `${yBubble}px`;
                    mesh.userData.bubbleElement.style.opacity = 1;
                } else {
                    mesh.userData.bubbleElement.style.opacity = 0;
                }
            }
        }
    }
    
    // --- Day/Night Visual Cycle ---
    // Compute brightness factor: 1.0 = full day, 0.0 = full night
    // Cycle: 0-69 day(1.0), 70-79 dusk(1.0→0.0), 80-109 night(0.0), 110-119 dawn(0.0→1.0)
    let brightness = 1.0;
    if (currentDayCycle >= 80 && currentDayCycle < 110) {
        brightness = 0.0; // Night
    } else if (currentDayCycle >= 70 && currentDayCycle < 80) {
        brightness = 1.0 - (currentDayCycle - 70) / 10; // Dusk transition
    } else if (currentDayCycle >= 110) {
        brightness = (currentDayCycle - 110) / 10; // Dawn transition
    }
    // Interpolate sky and fog colors
    const skyColor = DAY_SKY.clone().lerp(NIGHT_SKY, 1 - brightness);
    scene.background = skyColor;
    scene.fog.color.copy(skyColor);
    // Adjust lights (night is dim but not too dark)
    ambientLight.intensity = 0.3 + brightness * 0.3; // 0.3 at night, 0.6 at day
    dirLight.intensity = 0.15 + brightness * 0.65; // 0.15 at night, 0.8 at day
    
    // Optional: Make water flow gently
    water.position.y = -0.6 + Math.sin(Date.now() * 0.001) * 0.1;
    
    // Update frontend countdown display
    const remaining = Math.max(0, (nextTickTime - Date.now()) / 1000);
    const countdownEl = document.getElementById("countdown");
    if(countdownEl) {
        countdownEl.innerText = remaining.toFixed(1);
    }
    
    renderer.render(scene, camera);
}

// Handle resizing
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

let isFixedCamera = false; // Always free camera

function applyCameraMode(save = true) {
    if (isFixedCamera) {
        // Redundant but keeping structure
        controls.enabled = false;
        camera.position.set(WORLD_SIZE, 30, WORLD_SIZE + 10);
        controls.target.set(WORLD_SIZE, 0, WORLD_SIZE);
        camera.lookAt(WORLD_SIZE, 0, WORLD_SIZE);
    } else {
        controls.enabled = true;
    }
}

// Initial setup
applyCameraMode(false);

function setCameraFixed(val) {
    isFixedCamera = val;
    applyCameraMode();
}

window.toggleCameraMode = function() {
    // Disabled
};

animate();
renderer.domElement.addEventListener('click', handleWorldClick);
