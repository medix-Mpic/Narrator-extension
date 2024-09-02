#!/bin/bash


# Optional: Create a virtual environment using conda
conda create --name narrator python=3.9 -y

# Activate the virtual environment
source activate narrator

#CUDA installation
pip install torch==2.2.2+cu118 -f https://download.pytorch.org/whl/torch_stable.html

# Install the required dependencies
pip install -r requirements.txt

# Install ffmpeg using conda
conda install -c conda-forge ffmpeg -y

echo "Installation complete. You can now run the server with 'uvicorn server:app --host 0.0.0.0 --port 5000'."
