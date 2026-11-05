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

## 🎬 Step 2b: Modelos de Video (Wan 2.2)

`generate_video` sin imagen usa Wan 2.2 TI2V 5B con nodos nativos de ComfyUI (sin custom nodes; requiere una versión con soporte de Wan 2.2). Mantiene el archivo fp16 existente, pero `UNETLoader` lo carga con `weight_dtype=fp8_e4m3fn`: el benchmark C_fp8 logró 121 frames/5 s a 24 fps en 1280×704 o 704×1280, 30 pasos uni_pc/simple, CFG 5, shift 8 y `VAEDecodeTiled` (tile 512, overlap 64, temporal 64/8). Son ~17 GB de pesos en disco; la carga fp8 con offload se midió en una RTX 3060 de 12 GB, pero el consumo cambia con el host y la carga concurrente. El broker libera la GPU igual que con SDXL. El timeout por defecto de 5B es 4200 s (`VIDEO_TIMEOUT_SECONDS`); el de A14B, 2700 s (`A14B_TIMEOUT_SECONDS`). Ambos incluyen espera en cola y carga fría desde el envío del prompt; no son promesas de duración. Al vencer se intenta retirar el prompt pendiente e interrumpir ComfyUI, sin garantía de cancelación; una interrupción puede afectar otra ejecución concurrente. Ajusta también el timeout del cliente MCP. Dos corridas C_fp8 medidas tardaron 1620.7–1903.6 s (~27–31.7 min) para 5 s, no una promesa de rendimiento. `draft` conserva la resolución y limita el clip a 2 s/49 frames; esa variante no fue medida. La generación E2E por MCP queda pendiente.

```
~/stack/comfyui/models/
├── diffusion_models/
│   └── wan2.2_ti2v_5B_fp16.safetensors          # 9.3GB
├── text_encoders/
│   └── umt5_xxl_fp8_e4m3fn_scaled.safetensors   # 6.3GB
└── vae/
    └── wan2.2_vae.safetensors                   # 1.3GB
```

```bash
cd ~/stack/comfyui/models/
HF=https://huggingface.co/Comfy-Org
curl -L -o diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
  "$HF/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors"
curl -L -o text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "$HF/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
curl -L -o vae/wan2.2_vae.safetensors \
  "$HF/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/vae/wan2.2_vae.safetensors"
```

---

## A14B I2V 480p (opción recomendada con imagen)

Requiere [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) instalado como custom node en ComfyUI (el nodo `UnetLoaderGGUF`); además de nodos Wan I2V, `KSamplerAdvanced`, `LoraLoaderModelOnly` y `SaveVideo`. Ubicar los archivos **con estos nombres exactos**:

```
models/unet/Wan2.2-I2V-A14B-HighNoise-Q4_K_S.gguf
models/unet/Wan2.2-I2V-A14B-LowNoise-Q4_K_S.gguf
models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors
models/loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors
models/vae/wan_2.1_vae.safetensors
models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
```

No descargar ni modificar los pesos automáticamente: consulta las páginas de origen, sus licencias y términos antes de instalarlos. La licencia MIT de **este código MCP** no cubre los pesos Wan, los GGUF derivados ni las LoRA. Los repositorios originales [TI2V-5B](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) e [I2V-A14B](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B) declaran Apache 2.0 para esos modelos; [Comfy-Org repackaged](https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged) identifica los pesos adaptados para ComfyUI. Revisa además los términos propios del GGUF distribuido por terceros (consulta el repositorio exacto de los archivos instalados) y de las [LoRA lightx2v](https://huggingface.co/lightx2v/Wan2.2-Distill-Loras) para redistribución y uso comercial. El workflow A14B coincide con el benchmark local: 4 pasos (2 high + 2 low), CFG 1, shift 5, euler/simple, 16 fps y 480×832 o transpuesto. Un único run con imagen de mapache y 81 frames tardó 489.2 s; no extrapolar a otros clips. La validación E2E de esta integración a través de MCP sigue pendiente; los tiempos anteriores corresponden al workflow de benchmark, no a una ejecución de esta versión del servidor MCP.

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
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl start comfyui.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop comfyui.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart comfyui.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active comfyui.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop llama-server.service
```

> **Importante**: El archivo en `/etc/sudoers.d/gpu-arbiter` debe tener permisos `0440` (`sudo chmod 0440 /etc/sudoers.d/gpu-arbiter`).

---

## ⚙️ Step 4: Systemd Services

### 1. Service ComfyUI Backend (`/etc/systemd/system/comfyui.service`)

```ini
[Unit]
Description=ComfyUI Backend Engine
After=network.target
# Conflicts=llama-server.service  # (handled by GPU Broker)

[Service]
Type=simple
User=<YOUR_USER>
WorkingDirectory=<HOME>/stack/comfyui
ExecStart=<HOME>/stack/comfyui/.venv/bin/python main.py --listen 127.0.0.1 --port 8188
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
User=<YOUR_USER>
WorkingDirectory=<HOME>/Sites/comfyui-mcp
Environment="PATH=<HOME>/Sites/comfyui-mcp/.venv/bin:/usr/bin"
Environment="COMFYUI_URL=http://127.0.0.1:8188"
Environment="COMFYUI_PUBLIC_URL=http://<YOUR_SERVER_IP>:8188"
Environment="MCP_PORT=8201"
Environment="MCP_HOST=0.0.0.0"
ExecStart=<HOME>/Sites/comfyui-mcp/.venv/bin/python -m comfyui_mcp.server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## 🌐 Step 5: Firewall (UFW)

Para permitir que otros nodos de la red LAN consuman el MCP en el puerto `8201` y descarguen imágenes del puerto `8188`:

```bash
sudo ufw allow from <YOUR_LAN_CIDR> to any port 8201 proto tcp comment "ComfyUI MCP HTTP"
sudo ufw allow from <YOUR_LAN_CIDR> to any port 8188 proto tcp comment "ComfyUI Direct Image Download"
sudo ufw reload
```
