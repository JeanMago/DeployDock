"""
Serviço de Alertas e Notificações Multicanal (Discord, Telegram, Slack e Webhook Customizado).

Envia alertas em tempo real para eventos de:
- Deploy concluído com sucesso ou falha/rollback
- Ataques bloqueados pelo WAF / Brute-Force
- Queda de contêineres ou Auto-Healing acionado
- Uso elevado de CPU / Memória RAM no servidor host
"""

import json
import logging
import os
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia canais de notificação, regras de disparo e histórico de alertas enviados."""

    def __init__(self) -> None:
        self._config_path = os.path.join(
            os.path.dirname(os.path.abspath(settings.REPOS_BASE_PATH)),
            ".deploydock_notifications.json",
        )
        self.config: Dict[str, Any] = {
            "enabled": True,
            "discord_webhook_url": "",
            "slack_webhook_url": "",
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "custom_webhook_url": "",
            "notify_on_deploy_success": True,
            "notify_on_deploy_failure": True,
            "notify_on_waf_block": True,
            "notify_on_container_down": True,
            "notify_on_high_resource": True,
            "cpu_threshold_percent": 85,
            "ram_threshold_percent": 85,
        }
        self.history: Deque[Dict[str, Any]] = deque(maxlen=100)
        self._last_resource_alert_ts: float = 0.0
        self._load_config()

    def _load_config(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        self.config.update(saved)
        except Exception as e:
            logger.warning(f"Não foi possível carregar configuração de notificações: {e}")

    def _save_config(self) -> None:
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Não foi possível salvar configuração de notificações: {e}")

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in updates.items():
            if k in self.config and v is not None:
                self.config[k] = v
        self._save_config()
        return self.config

    def get_overview(self) -> Dict[str, Any]:
        channels_configured: List[str] = []
        if self.config.get("discord_webhook_url", "").strip():
            channels_configured.append("discord")
        if self.config.get("slack_webhook_url", "").strip():
            channels_configured.append("slack")
        if (
            self.config.get("telegram_bot_token", "").strip()
            and self.config.get("telegram_chat_id", "").strip()
        ):
            channels_configured.append("telegram")
        if self.config.get("custom_webhook_url", "").strip():
            channels_configured.append("webhook")

        return {
            "config": self.config,
            "channels_configured": channels_configured,
            "history": list(self.history),
        }

    async def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Dispara notificação para todos os canais configurados se a regra estiver ativa.
        Mesmo sem webhook externo configurado, registra no histórico interno de alertas.
        """
        if not force and not self.config.get("enabled", True):
            return {"status": "disabled"}

        if not force:
            if event_type == "deploy_success" and not self.config.get("notify_on_deploy_success", True):
                return {"status": "skipped"}
            if event_type == "deploy_failure" and not self.config.get("notify_on_deploy_failure", True):
                return {"status": "skipped"}
            if event_type == "waf_block" and not self.config.get("notify_on_waf_block", True):
                return {"status": "skipped"}
            if event_type == "container_down" and not self.config.get("notify_on_container_down", True):
                return {"status": "skipped"}
            if event_type == "high_resource":
                if not self.config.get("notify_on_high_resource", True):
                    return {"status": "skipped"}
                if time.time() - self._last_resource_alert_ts < 300:
                    return {"status": "throttled"}
                self._last_resource_alert_ts = time.time()

        now_iso = datetime.now(timezone.utc).isoformat()
        color_map = {
            "success": 0x10B981,
            "info": 0x0EA5E9,
            "warning": 0xF59E0B,
            "error": 0xEF4444,
            "critical": 0xDC2626,
        }
        emoji_map = {
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "critical": "🚨",
        }
        emoji = emoji_map.get(severity, "🔔")
        color = color_map.get(severity, 0x0EA5E9)

        delivered_channels: List[str] = []
        errors: List[str] = []

        async with httpx.AsyncClient(timeout=6.0) as client:
            # 1. Discord Webhook
            discord_url = (self.config.get("discord_webhook_url") or "").strip()
            if discord_url:
                try:
                    resp = await client.post(
                        discord_url,
                        json={
                            "username": "DeployDock Monitor",
                            "embeds": [
                                {
                                    "title": f"{emoji} {title}",
                                    "description": message,
                                    "color": color,
                                    "timestamp": now_iso,
                                    "footer": {"text": f"DeployDock • {event_type}"},
                                }
                            ],
                        },
                    )
                    if resp.status_code < 400:
                        delivered_channels.append("discord")
                    else:
                        errors.append(f"Discord HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"Discord: {e}")

            # 2. Slack Webhook
            slack_url = (self.config.get("slack_webhook_url") or "").strip()
            if slack_url:
                try:
                    resp = await client.post(
                        slack_url,
                        json={
                            "text": f"*{emoji} {title}*\n{message}\n_DeployDock • {event_type}_"
                        },
                    )
                    if resp.status_code < 400:
                        delivered_channels.append("slack")
                    else:
                        errors.append(f"Slack HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"Slack: {e}")

            # 3. Telegram Bot API
            tg_token = (self.config.get("telegram_bot_token") or "").strip()
            tg_chat = (self.config.get("telegram_chat_id") or "").strip()
            if tg_token and tg_chat:
                try:
                    tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                    resp = await client.post(
                        tg_url,
                        json={
                            "chat_id": tg_chat,
                            "text": f"{emoji} <b>{title}</b>\n\n{message}\n\n<code>DeployDock • {event_type}</code>",
                            "parse_mode": "HTML",
                        },
                    )
                    if resp.status_code < 400:
                        delivered_channels.append("telegram")
                    else:
                        errors.append(f"Telegram HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"Telegram: {e}")

            # 4. Webhook Customizado (JSON POST)
            custom_url = (self.config.get("custom_webhook_url") or "").strip()
            if custom_url:
                try:
                    resp = await client.post(
                        custom_url,
                        json={
                            "app": "DeployDock",
                            "event_type": event_type,
                            "severity": severity,
                            "title": title,
                            "message": message,
                            "metadata": metadata or {},
                            "timestamp": now_iso,
                        },
                    )
                    if resp.status_code < 400:
                        delivered_channels.append("webhook")
                    else:
                        errors.append(f"Webhook HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"Webhook: {e}")

        entry = {
            "id": f"notif-{int(time.time() * 1000)}",
            "timestamp": now_iso,
            "event_type": event_type,
            "severity": severity,
            "title": title,
            "message": message,
            "channels": delivered_channels if delivered_channels else ["painel_interno"],
            "errors": errors,
        }
        self.history.appendleft(entry)
        return entry


notification_manager = NotificationService()
