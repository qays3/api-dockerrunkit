from fastapi import FastAPI, HTTPException, Query, Request
from hashlib import sha384
from urllib.parse import unquote
import subprocess
import re
import os
import threading
import logging
import time

app = FastAPI()

log_file = "portidentification.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

active_ports = set()
lock = threading.Lock()

STATIC_API_KEY = os.getenv("STATIC_API_KEY", "4z9KNy6]vTRnzVD#;:Nn^I'S3]B'}{h%")
hashed_static_api_key = sha384(STATIC_API_KEY.encode()).hexdigest()

def log_message(message: str):
    logging.info(message)

def is_port_in_use(port: int):
    result = subprocess.run(f"docker ps --format '{{{{.Ports}}}}' | grep -oP '\\d+(?=->)'", shell=True, capture_output=True, text=True)
    used_ports = result.stdout.strip().split("\n") if result.stdout else []
    return str(port) in used_ports

def find_unused_port():
    start_port = 40000
    end_port = 59000

    with lock:
        for port in range(start_port, end_port):
            if port not in active_ports and not is_port_in_use(port):
                active_ports.add(port)
                log_message(f"Unused port found: {port}")
                return port
    raise Exception("No available ports")

def confirm_port_is_available(port: int, retries: int = 5, delay: int = 1):
    for _ in range(retries):
        if not is_port_in_use(port):
            return True
        time.sleep(delay)
    return False

def run_container(decoded_command, unused_port):
    decoded_command = re.sub(r'-p (\d+):', f'-p {unused_port}:', decoded_command)
    try:
        subprocess.Popen(["./run_and_stop.sh", decoded_command])
        log_message(f"Container started with command: {decoded_command} on port {unused_port}")
    except Exception as e:
        cleanup_port(unused_port)
        log_message(f"Failed to execute command: {decoded_command}. Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute command: {e}")

def cleanup_port(unused_port):
    with lock:
        if unused_port in active_ports:
            active_ports.remove(unused_port)
            log_message(f"Port {unused_port} freed after cleanup")

@app.get("/runcmd/")
async def run_command(command: str, api_key: str = Query(...), request: Request = None):
    if api_key != hashed_static_api_key:
        log_message(f"Unauthorized API key attempt.")
        raise HTTPException(status_code=401, detail="Invalid API key.")

    decoded_command = unquote(command)

    if not decoded_command.startswith("docker"):
        log_message(f"Invalid command attempt: {decoded_command}")
        raise HTTPException(status_code=400, detail="Invalid command. Only 'docker' commands are allowed.")

    forbidden_patterns = ["&&", ";", "|", "`", "$(", "${"]
    if any(pattern in decoded_command for pattern in forbidden_patterns):
        log_message(f"Command with invalid characters attempted: {decoded_command}")
        raise HTTPException(status_code=400, detail="Invalid characters in command.")

    try:
        unused_port = find_unused_port()

        if not confirm_port_is_available(unused_port):
            cleanup_port(unused_port)
            raise HTTPException(status_code=500, detail="Port allocation failed after confirmation.")

        thread = threading.Thread(target=run_container, args=(decoded_command, unused_port))
        thread.start()
        return {"message": "Command is running in the background.", "unused_port": unused_port}
    except Exception as e:
        log_message(f"No available ports: {e}")
        raise HTTPException(status_code=500, detail=f"No available ports: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
