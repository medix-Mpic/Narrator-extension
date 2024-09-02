# Use the base image with CUDA support
ARG BASE=nvidia/cuda:11.8.0-base-ubuntu22.04
FROM ${BASE}

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Python, pip, and ffmpeg
RUN apt-get update && \
    apt-get install -y python3 python3-pip ffmpeg

# Install the required Python packages
RUN pip3 install --no-cache-dir -r requirements.txt

# Set environment variable to accept license terms
ENV COQUI_TOS_AGREED=1

# Run the preload model script to download the model and accept license terms
RUN python3 download_model.py

# Expose the port the FastAPI app will run on
EXPOSE 5000

# Command to run the FastAPI server with Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5000"]
