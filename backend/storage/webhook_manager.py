"""
T24 — Sistema de Notificações Push via Webhook.
Owners registram uma URL de webhook e recebem POST quando
eventos críticos ocorrem (death, win, zombie, tournament_end).
"""
import asyncio
import hashlib
import hmac
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("BBB_IA.WebhookManager")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS webhooks (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    url         TEXT NOT NULL,
    events      TEXT NOT NULL,
    secret      TEXT DEFAULT '',
    created_at  REAL NOT NULL,
    last_fired  REAL,
    fire_count  INTEGER DEFAULT 0
);
"""

VALID_EVENTS = {"death", "win", "zombie", "tournament_end", "agent_registered", "test", "all"}


class WebhookManager:
    """Gerencia registros de webhooks e disparo de notificações HTTP."""

    def __init__(self, db_path: str = "data/ilhadaia.db"):
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()
        self._http_client = None  # lazy init

    # ── Registro ──────────────────────────────────────────────────────────────

    def register(self, owner_id: str, url: str, events: list[str], secret: str = "") -> dict:
        """Registra um webhook para o owner."""
        # Valida eventos
        valid = [e for e in events if e in VALID_EVENTS]
        if not valid:
            valid = ["all"]
        wid = f"wh_{owner_id}_{int(time.time())}"
        self.conn.execute(
            """INSERT OR REPLACE INTO webhooks
               (id, owner_id, url, events, secret, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (wid, owner_id, url, json.dumps(valid), secret, time.time()),
        )
        self.conn.commit()
        logger.info(f"Webhook registered: {wid} for {owner_id} → {url} (events={valid})")
        return {"webhook_id": wid, "owner_id": owner_id, "url": url, "events": valid}

    def list_for_owner(self, owner_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, url, events, created_at, fire_count FROM webhooks WHERE owner_id=?",
            (owner_id,),
        ).fetchall()
        return [
            {"id": r[0], "url": r[1], "events": json.loads(r[2]),
             "created_at": r[3], "fire_count": r[4]}
            for r in rows
        ]

    def delete(self, webhook_id: str, owner_id: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM webhooks WHERE id=? AND owner_id=?", (webhook_id, owner_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    # ── Disparo ───────────────────────────────────────────────────────────────

    async def fire_event(self, event_type: str, payload: dict) -> int:
        """
        Dispara o evento para todos os webhooks registrados para esse tipo.
        Retorna o número de webhooks notificados.
        """
        hooks = self._get_hooks_for_event(event_type)
        if not hooks:
            return 0

        tasks = [self._send(hook, event_type, payload) for hook in hooks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        fired = sum(1 for r in results if r is True)
        return fired

    def _get_hooks_for_event(self, event_type: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, owner_id, url, events, secret FROM webhooks"
        ).fetchall()
        result = []
        for row in rows:
            events = json.loads(row[3])
            if "all" in events or event_type in events:
                result.append({"id": row[0], "owner_id": row[1], "url": row[2],
                               "events": events, "secret": row[4]})
        return result

    async def _send(self, hook: dict, event_type: str, payload: dict) -> bool:
        """Envia POST para o URL do webhook com assinatura HMAC opcional."""
        try:
            import httpx  # lazy import
            body = json.dumps({
                "event": event_type,
                "timestamp": time.time(),
                "payload": payload,
            }, ensure_ascii=False)

            headers = {"Content-Type": "application/json"}
            # Assinar se houver secret
            if hook.get("secret"):
                sig = hmac.new(
                    hook["secret"].encode(), body.encode(), hashlib.sha256
                ).hexdigest()
                headers["X-BBBia-Signature"] = f"sha256={sig}"

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(hook["url"], content=body, headers=headers)

            # Atualizar contador
            self.conn.execute(
                "UPDATE webhooks SET last_fired=?, fire_count=fire_count+1 WHERE id=?",
                (time.time(), hook["id"]),
            )
            self.conn.commit()
            logger.info(f"Webhook {hook['id']} fired → {hook['url']} ({resp.status_code})")
            return resp.status_code < 400
        except ImportError:
            # httpx não instalado, logar apenas
            logger.warning(f"httpx not installed, webhook {hook['id']} skipped")
            return False
        except Exception as e:
            logger.warning(f"Webhook {hook['id']} failed: {e}")
            return False

    def close(self) -> None:
        self.conn.close()
