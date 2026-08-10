# Guía de Instalación del Servidor Backend (ComfyUI & GPU Broker)

> ⚠️ **Nota de Separación de Componentes**: Este repositorio (`comfyui-mcp`) contiene **únicamente el adaptador MCP**. Para que el sistema funcione, debes tener desplegado el servidor backend de ComfyUI, los modelos SDXL en disco y el servicio de arbitraje de GPU en la máquina host.

---

## 📋 Requisitos del Servidor Host

- **Sistema Operativo**: Linux (Pop!_OS 22.04 LTS / Ubuntu 22.04 LTS recomendado)
- **GPU**: NVIDIA RTX 3060 (12GB VRAM) o superior.
- **Drivers & CUDA**: NVIDIA Driver >= 535, CUDA Toolkit 12.x.
- **Python**: Python 3.11 / 3.12 con soporte PyTorch CUDA (`torch>=2.2.0+cu121`).

---

## 🛠️ Step 1: Instalación de ComfyUI Engine

1. **Clonar ComfyUI**:
   ```bash
   mkdir -p ~/stack
   cd ~/stack
   git clone https://github.com/comfyanonymous/ComfyUI.git comfyui
   cd comfyui
   ```

2. **Crear Entorno Virtual con CUDA**:
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   uv pip install -r requirements.txt
   ```

3. **Instalar Nodos Personalizados (Impact Pack)**:
   ```bash
   cd custom_nodes
   git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack.git
   cd ComfyUI-Impact-Pack
   python install.py
   ```

---

## 📦 Step 2: Descarga y Estructura de Modelos SDXL

Los modelos deben ubicarse en la estructura estándar de ComfyUI (`~/stack/comfyui/models/`):

```
~/stack/comfyui/models/
├── checkpoints/
│   ├── RealVisXL_V4.0.safetensors         # Preset 'producto'
│   ├── juggernautXL_ragnarokBy.safetensors # Preset 'realista' (default)
│   └── animagine-xl-3.1.safetensors       # Preset 'anime'
├── loras/
│   ├── Stylized_Setting_SDXL.safetensors
│   └── sdxl-lightning-4step.safetensors
└── vae/
    └── sdxl_vae.safetensors
```

### Script de Descarga Rápida (Ejemplo)

```bash
cd ~/stack/comfyui/models/checkpoints/

# Download RealVisXL V4.0
curl -L -o RealVisXL_V4.0.safetensors "https://civitai.com/api/download/models/361593?type=Model&format=SafeTensor"

# Download Juggernaut XL Ragnarok
curl -L -o juggernautXL_ragnarokBy.safetensors "https://civitai.com/api/download/models/782002?type=Model&format=SafeTensor"
```

---

## ⚡ Step 3: Configuración del GPU Broker & Arbiter

En servidores donde la GPU de 12GB se comparte entre un LLM (`llama-server`) y ComfyUI, se requiere el mecanismo de arbitraje para conmutar servicios sin agotar VRAM.

### 1. Script GPU Broker (`~/stack/gpu-broker/gpu-broker.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-wake_comfyui}"

if [ "$ACTION" = "wake_comfyui" ]; then
    if systemctl is-active --quiet llama-server.service; then
        echo "Deteniendo llama-server para liberar VRAM..."
        sudo systemctl stop llama-server.service
    fi
    if ! systemctl is-active --quiet comfyui.service; then
        echo "Iniciando comfyui.service..."
        sudo systemctl start comfyui.service
    fi
fi
```

### 2. Reglas de Sudoers (`/etc/sudoers.d/gpu-arbiter`)

Permite la gestión de servicios sin contraseña para el usuario de ejecución:

```ini
# /etc/sudoers.d/gpu-arbiter
# Permisos limitados para el arbitraje de GPU
germani ALL=(ALL) NOPASSWD: /usr/bin/systemctl start comfyui.service
germani ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop comfyui.service
germani ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart comfyui.service
germani ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active comfyui.service
germani ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop llama-server.service
```

> **Importante**: El archivo en `/etc/sudoers.d/gpu-arbiter` debe tener permisos `0440` (`sudo chmod 0440 /etc/sudoers.d/gpu-arbiter`).

---

## ⚙️ Step 4: Systemd Services

### 1. Service ComfyUI Backend (`/etc/systemd/system/comfyui.service`)

```ini
[Unit]
Description=ComfyUI Backend Engine
After=network.target
Conflicts=llama-server.service

[Service]
Type=simple
User=germani
WorkingDirectory=/home/germani/stack/comfyui
ExecStart=/home/germani/stack/comfyui/.venv/bin/python main.py --listen 127.0.0.1 --port 8188
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Service ComfyUI MCP (`/etc/systemd/system/comfyui-mcp.service`)

```ini
[Unit]
Description=ComfyUI MCP Server (FastMCP HTTP)
After=network.target comfyui.service

[Service]
Type=simple
User=germani
WorkingDirectory=/home/germani/Sites/comfyui-mcp
Environment="PATH=/home/germani/Sites/comfyui-mcp/.venv/bin:/usr/bin"
Environment="COMFYUI_URL=http://127.0.0.1:8188"
Environment="COMFYUI_PUBLIC_URL=http://192.168.68.108:8188"
Environment="MCP_PORT=8201"
Environment="MCP_HOST=0.0.0.0"
ExecStart=/home/germani/Sites/comfyui-mcp/.venv/bin/python -m comfyui_mcp.server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## 🌐 Step 5: Firewall (UFW)

Para permitir que otros nodos de la red LAN consuman el MCP en el puerto `8201` y descarguen imágenes del puerto `8188`:

```bash
sudo ufw allow from 192.168.68.0/24 to any port 8201 proto tcp comment "ComfyUI MCP HTTP"
sudo ufw allow from 192.168.68.0/24 to any port 8188 proto tcp comment "ComfyUI Direct Image Download"
sudo ufw reload
```
