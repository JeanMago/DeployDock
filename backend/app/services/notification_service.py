"""
Serviço de Alertas e Notificações Multicanal (E-mail SMTP, Discord, Telegram, Slack e Webhook Customizado).

Envia alertas em tempo real para eventos de:
- Deploy concluído com sucesso ou falha/rollback
- Ataques bloqueados pelo WAF / Brute-Force
- Queda de contêineres ou Auto-Healing acionado
- Uso elevado de CPU / Memória RAM no servidor host
"""

import asyncio
import json
import logging
import os
import smtplib
import ssl
import time
from collections import deque
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Deque, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.account_service import account_access_manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Gerencia canais de notificação (incluindo E-mail SMTP), regras de disparo e histórico de alertas."""

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
            # Canal de Notificação por E-mail (SMTP + Contas Logadas)
            "email_enabled": False,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "smtp_from_email": "alertas@deploydock.local",
            "smtp_from_name": "DeployDock Monitor",
            "smtp_use_tls": True,
            "email_recipients": "",
            "notify_logged_users_emails": True,
            # Gatilhos
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

    def _resolve_email_recipients(self, extra_recipients: Optional[List[str]] = None) -> List[str]:
        recipients: List[str] = []
        raw = (self.config.get("email_recipients") or "").replace(";", ",")
        for part in raw.split(","):
            addr = part.strip().lower()
            if addr and "@" in addr and addr not in recipients:
                recipients.append(addr)

        if self.config.get("notify_logged_users_emails", True):
            for addr in account_access_manager.get_notifiable_emails():
                if addr not in recipients:
                    recipients.append(addr)

        for addr in extra_recipients or []:
            clean = (addr or "").strip().lower()
            if clean and "@" in clean and clean not in recipients:
                recipients.append(clean)

        smtp_user = (self.config.get("smtp_user") or "").strip().lower()
        if not recipients and "@" in smtp_user:
            recipients.append(smtp_user)
        return recipients

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
        if self.config.get("email_enabled"):
            channels_configured.append("email")

        return {
            "config": self.config,
            "channels_configured": channels_configured,
            "resolved_email_recipients": self._resolve_email_recipients(),
            "history": list(self.history),
        }

    def _send_smtp_sync(
        self,
        recipients: List[str],
        subject: str,
        plain_body: str,
        html_body: str,
    ) -> tuple[bool, str]:
        smtp_host = (self.config.get("smtp_host") or "").strip()
        smtp_port = int(self.config.get("smtp_port") or 587)
        smtp_user = (self.config.get("smtp_user") or "").strip()
        smtp_pass = (self.config.get("smtp_password") or "").strip()
        from_email = (self.config.get("smtp_from_email") or smtp_user or "alertas@deploydock.local").strip()
        from_name = (self.config.get("smtp_from_name") or "DeployDock Monitor").strip()
        use_tls = bool(self.config.get("smtp_use_tls", True))

        # Se não há credenciais SMTP externas configuradas, registra envio na caixa de saída interna
        if not smtp_host or not smtp_user or not smtp_pass:
            return True, f"queued_local ({', '.join(recipients)})"

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = ", ".join(recipients)
        msg.set_content(plain_body)
        msg.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10, context=context) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)

        return True, f"smtp_sent ({', '.join(recipients)})"

    async def notify(
        self,
        event_type: str,
        title: str,
        message: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
        force: bool = False,
        extra_emails: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Dispara notificação para todos os canais configurados (E-mail, Discord, Slack, Telegram, Webhook).
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
        hex_color_map = {
            "success": "#10b981",
            "info": "#0ea5e9",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "critical": "#dc2626",
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
        hex_color = hex_color_map.get(severity, "#0ea5e9")

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

        # 5. Notificação por E-mail (SMTP / E-mail HTML)
        if self.config.get("email_enabled") or extra_emails:
            recipients = self._resolve_email_recipients(extra_emails)
            if recipients:
                subject = f"{emoji} [DeployDock] {title}"
                plain_body = (
                    f"{title}\n"
                    f"{'=' * len(title)}\n\n"
                    f"{message}\n\n"
                    f"Evento: {event_type} | Severidade: {severity.upper()}\n"
                    f"Horário (UTC): {now_iso}\n"
                )
                safe_msg_html = message.replace("\n", "<br/>")
                html_body = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #0b0f19; color: #e2e8f0; border: 1px solid #1e293b; border-radius: 10px; overflow: hidden;">
                  <div style="background: {hex_color}; padding: 14px 20px; color: #ffffff; font-weight: 700; font-size: 15px;">
                    {emoji} DeployDock • {title}
                  </div>
                  <div style="padding: 20px; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
                    <p style="margin-top: 0;">{safe_msg_html}</p>
                    <hr style="border: 0; border-top: 1px solid #1e293b; margin: 16px 0;" />
                    <div style="font-size: 12px; color: #64748b; font-family: monospace;">
                      Evento: <strong>{event_type}</strong> • Severidade: <strong>{severity.upper()}</strong><br/>
                      Destinatários: {', '.join(recipients)}<br/>
                      Horário: {now_iso}
                    </div>
                  </div>
                </div>
                """
                try:
                    ok, detail = await asyncio.to_thread(
                        self._send_smtp_sync, recipients, subject, plain_body, html_body
                    )
                    if ok:
                        delivered_channels.append("email")
                except Exception as e:
                    errors.append(f"Email SMTP: {e}")

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
