#!/usr/bin/env python3
"""
DeployDock - Script de teste de webhook do GitHub.

Simula o envio de um evento 'push' do GitHub com assinatura HMAC-SHA256 válida.
Permite testar a comunicação e o pipeline de GitOps localmente sem precisar de túneis externos (ngrok).

Uso:
    python scripts/test_webhook.py --repo https://github.com/usuario/repo.git --branch main
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import httpx

def main():
    parser = argparse.ArgumentParser(description="Testar webhook do GitHub no DeployDock")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/webhooks/github", help="URL do endpoint do webhook (pode ser http://localhost:8000 ou http://localhost/api/v1/webhooks/github)")
    parser.add_argument("--repo", required=True, help="URL do repositório Git cadastrado no projeto")
    parser.add_argument("--branch", default="main", help="Nome da branch (padrão: main)")
    parser.add_argument("--commit", default="abcdef1234567890abcdef1234567890abcdef12", help="SHA do commit")
    parser.add_argument("--secret", default="your-github-webhook-secret-here", help="Secret configurado no .env (GITHUB_WEBHOOK_SECRET)")

    args = parser.parse_args()

    # Monta payload simulando o GitHub push event
    payload = {
        "ref": f"refs/heads/{args.branch}",
        "after": args.commit,
        "repository": {
            "clone_url": args.repo,
            "name": args.repo.split("/")[-1].replace(".git", ""),
        },
        "head_commit": {
            "id": args.commit,
            "message": "Teste automatizado de GitOps",
            "author": {
                "name": "DeployDock Tester",
                "email": "test@deploydock.local"
            }
        }
    }

    body = json.dumps(payload).encode("utf-8")

    # Calcula assinatura HMAC-SHA256
    signature = "sha256=" + hmac.new(args.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": "test-delivery-id-001",
        "X-Hub-Signature-256": signature,
    }

    print(f"Enviando webhook para: {args.url}")
    print(f"Repositório: {args.repo} @ {args.branch}")
    print(f"Assinatura calculada: {signature[:18]}...")

    try:
        response = httpx.post(args.url, content=body, headers=headers, timeout=10.0)
        print(f"\nStatus Code: {response.status_code}")
        print(f"Resposta: {response.text}")

        if response.status_code == 202:
            print("\n✅ Webhook aceito! O DeployDock iniciou o pipeline de deploy em background.")
        elif response.json().get("status") == "no_matching_project":
            print("\n⚠️ O webhook foi recebido com sucesso, mas nenhum projeto com essa URL e Branch foi encontrado no banco.")
            print("Dica: Cadastre um projeto primeiro no Dashboard com essa mesma URL e com 'auto_deploy: true'.")
    except Exception as e:
        print(f"\n❌ Erro ao enviar requisição: {e}")

if __name__ == "__main__":
    main()
