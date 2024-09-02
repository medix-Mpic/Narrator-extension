import os
from TTS.utils.manage import ModelManager

# Set environment variable to bypass license acceptance prompt
os.environ["COQUI_TOS_AGREED"] = "1"

def download_model():
    model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
    print("⏳Downloading model")
    ModelManager().download_model(model_name)

if __name__ == "__main__":
    download_model()
