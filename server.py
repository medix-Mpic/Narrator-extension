import subprocess
import sys
from fastapi import FastAPI, Request ,WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from model.model import Model 
from model.device import device
import asyncio  
import io
import time
import re
import threading
from collections import deque
from queue import Queue
import logging
import os


app = FastAPI()


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def clean_text(text):
    cleaned_text = re.sub(r'\[.*?\]', '', text)
    cleaned_text = re.sub(r'\[\d+\]', '', cleaned_text)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

buffer_size = 10
buffer = Queue(maxsize=buffer_size)



# Global variables
ffplay_proc = None
stop_playback_event = threading.Event()
tts_model = None
preload = False 
Finished = False
# Set up a list of active WebSocket connections
active_connections = set()

def preload_model():
    global preload, tts_model
    
    try:
        tts_model = Model()
        tts_model.load_model()
        tts_model.load_speaker_embedding()
        preload = True
        logging.info("Model preloaded successfully.")
    except Exception as e:
        logging.error(f"Error during model preloading: {e}")
        raise HTTPException(status_code=500, detail="Model preloading failed")


@app.get("/modelCheck")
async def modelCheck():
    global preload
    if not preload :
        preload_model()
        return {"status": "preloading"}
        
    return {"status": "ready"}

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


playback_complete_event = threading.Event()  # New event to signal playback completion

def run_ffplay(ffplay_cmd, audio_stream=None):
    global ffplay_proc, stop_playback_event, playback_complete_event
    
    try:
        if device == "cuda":
            with subprocess.Popen(ffplay_cmd, stdin=subprocess.PIPE) as ffplay_proc:
                for chunk in audio_stream:
                    if stop_playback_event.is_set():
                        break
                    ffplay_proc.stdin.write(chunk)
                ffplay_proc.stdin.flush()
        else:
            with subprocess.Popen(ffplay_cmd, stdin=subprocess.PIPE) as ffplay_proc:
                ffplay_proc.stdin.write(audio_stream)
                ffplay_proc.stdin.flush()

        ffplay_proc.stdin.close()
        ffplay_proc.wait()
    except BrokenPipeError:
        pass
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        playback_complete_event.set()  # Signal that playback is complete
        
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global active_connections
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep the connection open
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await websocket.close()

        

def wait_for_stream():
    global playback_complete_event, Finished
    
    playback_complete_event.wait()  # Wait until playback is complete
    Finished = True
    
    # Notify all active WebSocket connections when playback is complete
    for connection in active_connections.copy():
        try:
            asyncio.run(connection.send_json({"status": "finished"}))
        except Exception as e:
            logging.error(f"Error sending WebSocket message: {e}")
            #print(f"Error sending WebSocket message: {e}")
            active_connections.remove(connection)
    Finished = False  # Reset the Finished flag for next operation


@app.get("/tts")
async def tts_status():
    global Finished
    
    if Finished:
        print("------------------F I N I S H E D -----------------") #FOR DEBUGGING
        Finished = False #Set finished back to false so the text can be highlighted again
        return {"status":"finished"}
    else:
        print("------------------S T I L L     P L A Y I N G ----------------") #FOR DEBUGGING
        return {"status":"still playing"}
    
    
@app.post("/tts")
async def run_tts(request: Request):
    global ffplay_proc, stop_playback_event, playback_complete_event , Finished
    Finished = False
    data = await request.json()
    text = data.get('text', "")
    text_to_speech = clean_text(text)
    voice = data.get('voice', "Morgan")
    speed = data.get('speed', 1.0)

    tts_model.load_speaker_embedding(voice=voice)
    try:
        if device == "cpu":
            model_input = {
                "text": text_to_speech,
                "language": "en"
            }
            start = time.perf_counter()
            generated_audio = tts_model.predict_inference(model_input)
            end = time.perf_counter()
            #print(f"Time to generate audio on CPU: {end-start}s", file=sys.stderr)
            logging.info(f"Time to generate audio on CPU: {end-start:.2f}s")
            
            ffplay_cmd = [
                "ffplay", "-nodisp", "-autoexit", 
                "-af", f"atempo={speed}",
                "-f", "s16le", "-ar", "24000", "-ac", "1", "-"
            ]
        elif device == "cuda":
            model_input = {
                "text": text_to_speech,
                "chunk_size": 16,
                "language": "en"
            }
            start = time.perf_counter()
            audio_stream = tts_model.predict_stream(model_input)
            end = time.perf_counter()
            #print(f"Time to generate audio: {end-start}s", file=sys.stderr)
            logging.info(f"Time to generate audio on CUDA: {end-start:.2f}s")
            
            ffplay_cmd = [
                "ffplay", "-nodisp", "-autoexit", 
                "-af", f"atempo={speed}",
                "-f", "s16le", "-ar", "24000", "-ac", "1", "-"
            ]
    except Exception as e :
        logging.error(f"Error during TTS processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to process TTS")
            
    # Terminate any ongoing playback before starting new
    if ffplay_proc and ffplay_proc.poll() is None:
        stop_playback_event.set()
        ffplay_proc.terminate()
        ffplay_proc.wait()

    stop_playback_event.clear()
    playback_complete_event.clear()  # Reset the playback completion event

    threading.Thread(target=run_ffplay, args=(ffplay_cmd, generated_audio if device == "cpu" else audio_stream)).start()

    # Wait for playback to complete
    
    threading.Thread(target=wait_for_stream).start()

    return {"message": "Audio playback finished"}
    
        
        

@app.post("/stop")
async def stop_tts():
    global ffplay_proc, stop_playback_event
    if ffplay_proc and ffplay_proc.poll() is None:
        stop_playback_event.set()
        ffplay_proc.terminate()
        ffplay_proc.wait()
        ffplay_proc = None
        return {"message": "Playback stopped"}
    else:
        return {"message": "No playback to stop"}
    
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
