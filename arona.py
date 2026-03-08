import ollama
import json
import os
import subprocess
import time
import sys
import threading
import re

# --- CONFIGURATION ---
BASE = "/home/loya/Arona-Project"
EARS = f"{BASE}/models/ggml-base.en.bin"
VOICE = f"{BASE}/models/en_US-amy-medium.onnx"
BRAIN = "llama3.2:1b"
MEMORY_FILE = f"{BASE}/memory.json"
PERSONA_FILE = f"{BASE}/persona.txt"


def get_personality():
    """Reads the persona from the text file."""
    try:
        with open(PERSONA_FILE, 'r') as f:
            content = f.read().strip()
        return {'role': 'system', 'content': content}
    except Exception as e:
        # Fallback if the file is missing
        return {'role': 'system', 'content': "You are Arona, a moody AI."}

# Change this in your load_memory function or where you start the chat:
PERSONALITY = get_personality()

# --- FUNCTIONS ---

def speak(text):
    """The Mouth: Pipes Piper TTS into the 'play' command for effects."""
    safe_text = text.replace('"', '').replace("'", "")
    
    # NOTE: You need the 'sox' package for 'play' to work.
    # If this fails, run: sudo pacman -S sox
    command = (
        f'piper-tts --model {BASE}/models/en_US-amy-medium.onnx --output_raw | '
        f'play -q -t raw -r 22050 -e signed-integer -b 16 -c 1 - '
        f'pitch 380 treble +4 bass +2 tempo 1.05'
    )

    try:
        subprocess.run(
            command, shell=True, input=safe_text.encode('utf-8'),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"\n[Voice Error]: {e}")

def listen_manual():
    """The Ears: Records audio until you hit Enter."""
    TEMP_WAV = "/tmp/arona_manual.wav"
    
    # Start arecord
    proc = subprocess.Popen(
        ["arecord", "-r", "16000", "-f", "S16_LE", "-c", "1", TEMP_WAV],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    input(f"\033[91m●\033[0m RECORDING... Press ENTER to stop.")
    
    proc.terminate()
    proc.wait() 
    
    # Transcribe
    print(f"\033[94m●\033[0m Arona is listening to your voice...", end="\r")
    result = subprocess.run(
        ["whisper-cli", "-m", EARS, "-f", TEMP_WAV, "-nt"],
        capture_output=True, text=True
    )
    
    print(" " * 50, end="\r") # Clear line
    return re.sub(r'\[.*?\]', '', result.stdout).strip()

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f: return json.load(f)
        except: return [PERSONALITY]
    return [PERSONALITY]

def save_memory(messages):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(messages[-50:], f)

def typewriter(text):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.02)
    print()

# --- THE MAIN LOOP ---

def chat():
    messages = load_memory()
    C_BLUE, C_RED, C_GREEN, C_RESET = "\033[94m", "\033[91m", "\033[92m", "\033[0m"

    print(f"{C_BLUE}●{C_RESET} Arona: System Online. I'm here, I guess.")
    
    while True:
        try:
            print(f"\n{C_BLUE}●{C_RESET} Press ENTER to speak (or type a message/exit): ", end="")
            user_cmd = input()
            
            # 1. Exit Logic
            if user_cmd.lower() in ['exit', 'quit', 'sleep']:
                farewell = "Understood. System hibernating. See you soon, Loya!"
                print(f"{C_RED}●{C_RESET} Arona: {farewell}")
                speak(farewell)
                save_memory(messages)
                break
                
            # 2. Input Logic (Manual Listen vs Typing)
            if user_cmd == "":
                user_input = listen_manual()
                if not user_input:
                    print(f"{C_RED}●{C_RESET} Arona: You said absolutely nothing. Was that a test?")
                    continue
            else:
                user_input = user_cmd
                    
            print(f"{C_BLUE}●{C_RESET} Loya: {user_input}")
            messages.append({'role': 'user', 'content': user_input})

            # 3. Brain Logic (Ollama)
            print(f"{C_RED}●{C_RESET} Arona: Thinking... (don't rush me)", end="\r")
            
            response = ollama.chat(model=BRAIN, messages=messages, keep_alive='3h')
            arona_reply = response['message']['content']
            
            print(" " * 50, end="\r") # Clear "Thinking"
            print(f"{C_GREEN}●{C_RESET} Arona: ", end="")
            
            # 4. Output Logic (Speech + Text)
            threading.Thread(target=speak, args=(arona_reply,), daemon=True).start()
            typewriter(arona_reply) 
            
            messages.append({'role': 'assistant', 'content': arona_reply})
            save_memory(messages)

        except EOFError:
            print(f"\n{C_RED}●{C_RESET} Arona: Force shutdown? Rude. Saving memory...")
            save_memory(messages)
            break
        except Exception as e:
            print(f"\n{C_RED}●{C_RESET} Arona Error: {e}")
            time.sleep(2) # Give you time to read the error

if __name__ == "__main__":
    chat()