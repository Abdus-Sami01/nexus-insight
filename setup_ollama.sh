#!/bin/bash

# Check if Ollama is installed
if ! command -v ollama &> /dev/null
then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.ai/install.sh | sh
else
    echo "Ollama version: $(ollama --version)"
fi

# Detect RAM for model selection
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
echo "Detected RAM: ${TOTAL_RAM}GB"

if [ "$TOTAL_RAM" -ge 48 ]; then
    echo "Pulling Qwen 2.5 72B (Large model)..."
    ollama pull qwen2.5:72b
elif [ "$TOTAL_RAM" -ge 16 ]; then
    echo "Pulling Qwen 2.5 14B (Medium model)..."
    ollama pull qwen2.5:14b
else
    echo "Pulling Qwen 2.5 7B and Mistral 7B (Light models)..."
    ollama pull qwen2.5:7b
    ollama pull mistral:7b
fi

ollama list
echo "Ollama setup complete."
