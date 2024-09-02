import base64
import io
import logging
import os
import wave

import numpy as np
import torch
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir
from TTS.utils.manage import ModelManager
from model.device import device
import time


# This is one of the speaker voices that comes with xtts
#SPEAKER_NAME = "Claribel Dervla"
#SAMPLE_WAV_PATH = "morg.wav"
#SAMPLE_WAV_PATH = None
SPEAKER_NAME = {"Claribel":'Claribel Dervla',
              "Daisy":'Daisy Studious',
              "Gracie":'Gracie Wise',
              "Tammie":'Tammie Ema',
              "Alison":'Alison Dietlinde',
              "Ana":'Ana Florence'
              }

voices = { "Morgan" : "voices/morganFreeman.wav" ,
          "Hopkins" : "voices/hopkins.wav" ,
          "Dave": "voices/Dave.wav",
          "Simmons" :"voices/simmons.wav"}

logging.basicConfig(level=logging.INFO)



class Model:
    def __init__(self, **kwargs):
        self.model = None
        self.speaker = None
    def load_speaker_embedding(self, voice = "Morgan"):
        start = time.perf_counter()
        if voice in SPEAKER_NAME.keys() :
                self.speaker = {
                    "speaker_embedding": self.model.speaker_manager.speakers[SPEAKER_NAME[voice]][
                        "speaker_embedding"
                    ]
                    .cpu()
                    .squeeze()
                    .half()
                    .tolist(),
                    "gpt_cond_latent": self.model.speaker_manager.speakers[SPEAKER_NAME[voice]][
                        "gpt_cond_latent"
                    ]
                    .cpu()
                    .squeeze()
                    .half()
                    .tolist(),
                }
        else:
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(voices[voice])
            self.speaker = {
                "speaker_embedding": speaker_embedding
                .cpu()
                .squeeze()
                .half()
                .tolist(),
                "gpt_cond_latent" : gpt_cond_latent.cpu()
                .squeeze()
                .half()
                .tolist(),
            }
        end = time.perf_counter()   
        logging.info(f"Loading speaker embeddings took {end-start}.s") 
    
    def load_model(self):
        start = time.perf_counter()
        #device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Using device: {device}")
        
        model_name = "tts_models/multilingual/multi-dataset/xtts_v2"
        logging.info("⏳Downloading model")
        ModelManager().download_model(model_name)
        
        model_path = os.path.join(
            get_user_data_dir("tts"), model_name.replace("/", "--")
        )

        config = XttsConfig()
        config.load_json(os.path.join(model_path, "config.json"))
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config, checkpoint_dir=model_path, eval=True)
        self.model.to(device)
        end = time.perf_counter()
        logging.info(f"Loading model took {end-start}.s")

        logging.info("🔥Model Loaded")
        
        

    def wav_postprocess(self, wav):
        """Post process the output waveform"""
        if isinstance(wav, list):
            wav = torch.cat(wav, dim=0)
        wav = wav.clone().detach().cpu().numpy()
        wav = np.clip(wav, -1, 1)
        wav = (wav * 32767).astype(np.int16)
        return wav

    def predict_stream(self, model_input):
        text = model_input.get("text")
        language = model_input.get("language", "en")
        
      
        
        
        speaker_embedding = (
            torch.tensor(self.speaker.get("speaker_embedding"))
            .unsqueeze(0)
            .unsqueeze(-1)
        )
        
        gpt_cond_latent = (
            torch.tensor(self.speaker.get("gpt_cond_latent"))
            .reshape((-1, 1024))
            .unsqueeze(0)
        )
        
     
     

        chunk_size = int(
            model_input.get("chunk_size", 150)
        )  # Ensure chunk_size is an integer
        add_wav_header = False
        
    
        streamer = self.model.inference_stream(
            text,
            language,
            gpt_cond_latent,
            speaker_embedding,
            stream_chunk_size=chunk_size,
            enable_text_splitting=True,
            temperature=0.75,
            repetition_penalty=10.9,
            length_penalty=0.9,
            top_k=70,
            top_p=0.92,
            
        )

        for chunk in streamer:
          
            processed_chunk = self.wav_postprocess(chunk)
            processed_bytes = processed_chunk.tobytes()
           
            yield processed_bytes
            
            
    def predict_inference(self, model_input):
        
        text = model_input.get("text")
        language = model_input.get("language", "en")
        
      
          
        
        speaker_embedding = (
            torch.tensor(self.speaker.get("speaker_embedding"))
            .unsqueeze(0)
            .unsqueeze(-1)
        )
        
        gpt_cond_latent = (
            torch.tensor(self.speaker.get("gpt_cond_latent"))
            .reshape((-1, 1024))
            .unsqueeze(0)
        )
        
        
           
            
        
        generated_audio = self.model.inference(
            text,
            language,
            gpt_cond_latent,
            speaker_embedding,
            enable_text_splitting=True,
        )
        
      
        wav = generated_audio.get("wav")
        #processed_generated_audio = self.wav_postprocess(wav)
        wav = torch.from_numpy(wav)
        wav = wav.clone().detach().cpu().numpy()
        wav = np.clip(wav, -1, 1)
        wav = (wav * 32767).astype(np.int16)
        processed_bytes = wav.tobytes()
        
        
        return processed_bytes
    