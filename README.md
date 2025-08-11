# Quick Start Guide

## Project Assumptions

This project makes the following assumptions:

1. **Docker Knowledge**: You are familiar with running dockerized systems and have Docker with Docker Compose installed on your machine.

2. **Google Cloud API Setup**: You have access to Google Cloud Platform and can obtain a Google Maps API key. You'll need to update the API key in either:
   - `backend/main.py` (GOOGLE_MAPS_API_KEY variable)
   - `docker-compose.yml` (GOOGLE_MAPS_API_KEY environment variable)

3. **LLM Model**: The system has been tested with `llama3.2` model, but should work with other compatible models. You'll need to pull the model after starting the services.

4. **Tool Installation**: You understand how to add custom tools to OpenWebUI:
   - Navigate to Workspaces → Tools
   - Add a new tool (e.g., name it "map")
   - Paste the contents of `google_maps_tool.py` and save

5. **UI Limitations**: Currently, the embedded map will display in the right sidebar as an artifact preview due to OpenWebUI limitations. For production use, we assume you would fork OpenWebUI and develop a custom UI to properly display the iframe within the chat interface.

6. **Architecture Design**: The tool uses event emitters to immediately return backend responses and construct HTML code for Google Maps embedding, while allowing the AI to process and present the data in natural language format.

## 1. GPU Setup (NVIDIA only)

### Install nvidia-container-toolkit:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
```

### Configure Docker for GPU:
```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Test GPU access:
```bash
docker run --rm --runtime=nvidia nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```

## 2. Configure Docker Compose

### For systems WITH GPU:
Edit `docker-compose.yml` ollama service to:

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11436:11434"
    volumes:
      - ollama:/root/.ollama
    runtime: nvidia
    environment:
      - OLLAMA_HOST=0.0.0.0
      - NVIDIA_VISIBLE_DEVICES=all
    restart: unless-stopped
```

### For systems WITHOUT GPU:
Remove/comment out the runtime and NVIDIA_VISIBLE_DEVICES lines.

## 3. Configure Google Maps API Key

Edit `google_maps_tool.py` and replace the API key:

```python
GOOGLE_MAPS_API_KEY: str = "YOUR_ACTUAL_API_KEY_HERE"
```

Get your API key from: https://console.cloud.google.com/apis/credentials

Required APIs:
- Places API
- Geocoding API  
- Maps Embed API

## 4. Start the Services

```bash
docker compose up -d
```

Wait for both containers to start (check with `docker compose logs -f`).

## 5. Pull AI Models

### Option A: Via Web Interface
1. Open http://localhost:3000
2. Click the model dropdown
3. Type a model name (e.g., `llama3.2`)
4. Click "Pull [model] from Ollama.com"

### Option B: Via Command Line

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

## 6. Install Custom Tool

1. Open http://localhost:3000 in your browser
2. Navigate to **Workspaces** → **Tools**
3. Click **Add Tool** or **Create New Tool**
4. Give it a name (e.g., "map" or "google_maps")
5. Paste the entire contents of `google_maps_tool.py`
6. Click **Save**

## 7. Access the Interface

Open http://localhost:3000 in your browser and start a new chat.

## 8. Test Google Maps Integration

Try these queries:
- "Find nearby cafes"
- "Search for restaurants near me"
- "Find gas stations"
- "Get directions from A to B"

**Note**: The embedded map will appear in the right sidebar as an artifact preview due to current OpenWebUI limitations.

## Troubleshooting

### Containers won't start:
```bash
docker compose logs -f
```

### Model download fails:
```bash
# Check Ollama status
docker compose exec ollama ollama list

# Manually pull model
docker compose exec ollama ollama pull [model-name]
```

### Google Maps not working:
- Verify API key in `google_maps_tool.py`
- Check API quotas in Google Cloud Console
- Ensure required APIs are enabled

### Out of memory:
- Use smaller models (135m, 0.5b, 2b)
- Reduce `docker-compose.yml` memory limits
- Close other applications

## Stop Services

```bash
docker compose down
```