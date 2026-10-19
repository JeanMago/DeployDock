#!/usr/bin/env bash
# ==============================================================================
# DeployDock — Instalador e Inicializador Automático de Produção
# Compatível com: Oracle Cloud (Ubuntu ARM64/AMD64) & Hostgrid / Hostinger VPS
# ==============================================================================
set -e

echo "============================================================"
echo "  DeployDock — Setup de Produção (Oracle Cloud / Hostgrid)  "
echo "============================================================"

# 1. Instalar Docker e Docker Compose se ainda não estiverem instalados
if ! command -v docker &> /dev/null; then
    echo "[1/5] Docker não encontrado. Instalando Docker Engine..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER" || true
else
    echo "[1/5] Docker já instalado: $(docker --version)"
fi

# 2. Criar arquivo de Swap de 2GB caso a VPS tenha pouca RAM (ex: 1GB) e não tenha Swap
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
    echo "[2/5] Configurando 2GB de memória Swap para estabilidade de builds..."
    sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    if ! grep -q "/swapfile" /etc/fstab; then
        echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null
    fi
else
    echo "[2/5] Swap já ativo."
fi

# 3. Liberar portas 80, 443 e 3000 no Firewall (Oracle Cloud iptables + UFW)
echo "[3/5] Liberando portas HTTP (80), HTTPS (443) e Painel (3000) no firewall..."
if command -v iptables &> /dev/null; then
    sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT || true
    sudo iptables -I INPUT 1 -p tcp --dport 443 -j ACCEPT || true
    sudo iptables -I INPUT 1 -p tcp --dport 3000 -j ACCEPT || true
    if command -v netfilter-persistent &> /dev/null; then
        sudo netfilter-persistent save || true
    fi
fi

if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        sudo ufw allow 22/tcp || true
        sudo ufw allow 80/tcp || true
        sudo ufw allow 443/tcp || true
        sudo ufw allow 3000/tcp || true
    fi
fi

# 4. Gerar arquivo .env de Produção se ainda não existir
PUBLIC_IP=$(curl -4 -s --max-time 5 https://ifconfig.me || curl -4 -s --max-time 5 https://api.ipify.org || echo "127.0.0.1")

if [ ! -f .env ]; then
    echo "[4/5] Gerando arquivo .env de produção (IP Público detectado: $PUBLIC_IP)..."
    SECRET_KEY=$(openssl rand -hex 32)
    DB_PASS=$(openssl rand -hex 16)
    WEBHOOK_SECRET=$(openssl rand -hex 20)
    ADMIN_PASS="Admin@$(openssl rand -hex 4)"
    SSLIP_DOMAIN="${PUBLIC_IP}.sslip.io"

    cat > .env <<EOF
# ==========================================================
# DeployDock — Configuração de Produção Gerada Automaticamente
# ==========================================================
POSTGRES_DB=deploydock
POSTGRES_USER=deploydock
POSTGRES_PASSWORD=${DB_PASS}
DATABASE_URL=postgresql+asyncpg://deploydock:${DB_PASS}@db:5432/deploydock

SECRET_KEY=${SECRET_KEY}
GITHUB_WEBHOOK_SECRET=${WEBHOOK_SECRET}

# Por padrão, utiliza sslip.io com o IP público da VPS (funciona sem precisar comprar domínio!).
# Caso tenha um domínio próprio apontado (*.seudominio.com), altere APPS_BASE_DOMAIN, DEPLOYDOCK_HOST e APPS_TLS_ENABLED=true.
APPS_BASE_DOMAIN=${SSLIP_DOMAIN}
DEPLOYDOCK_HOST=painel.${SSLIP_DOMAIN}
APPS_TLS_ENABLED=false
ACME_EMAIL=admin@${SSLIP_DOMAIN}
APPS_NETWORK=deploydock-apps
BACKEND_BIND_IP=127.0.0.1

CORS_ORIGINS=["http://painel.${SSLIP_DOMAIN}","http://${PUBLIC_IP}:3000","http://${PUBLIC_IP}","http://localhost:3000"]

INITIAL_ADMIN_USERNAME=admin
INITIAL_ADMIN_EMAIL=admin@${SSLIP_DOMAIN}
INITIAL_ADMIN_PASSWORD=${ADMIN_PASS}
EOF
    echo "------------------------------------------------------------"
    echo "  Arquivo .env criado com sucesso!"
    echo "  Usuário Admin Inicial: admin"
    echo "  Senha Admin Inicial:   ${ADMIN_PASS}"
    echo "  (Guarde esta senha ou consulte no arquivo .env)"
    echo "------------------------------------------------------------"
else
    echo "[4/5] Arquivo .env já existente. Mantendo configurações atuais."
fi

# 5. Subir os contêineres em Produção
echo "[5/5] Construindo e iniciando contêineres Docker em Produção..."
sudo docker compose up -d --build

echo ""
echo "============================================================"
echo "  DeployDock em Produção iniciado com sucesso!"
echo "  Painel via Traefik: http://painel.${PUBLIC_IP}.sslip.io"
echo "  Painel Porta 3000:  http://${PUBLIC_IP}:3000"
echo "============================================================"
