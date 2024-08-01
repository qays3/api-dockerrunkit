from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.security.api_key import APIKeyQuery
from urllib.parse import unquote
from hashlib import sha384
import subprocess
import re
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

app = FastAPI()


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


STATIC_API_KEY = os.getenv("STATIC_API_KEY", "your_secret_key_here")
hashed_static_api_key = sha384(STATIC_API_KEY.encode()).hexdigest()

def find_unused_port():
    try:
        output = subprocess.check_output(["./portidentification.sh"]).decode("utf-8").strip()
        return output
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find an unused port: {e}")

@app.get("/runcmd/")
@limiter.limit("300/minute")  
async def run_command(command: str, api_key: str = Query(...), request: Request = None):

    if api_key != hashed_static_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    

    decoded_command = unquote(command)
    

    if not decoded_command.startswith("docker"):
        raise HTTPException(status_code=400, detail="Invalid command. Only 'docker' commands are allowed.")
    

    forbidden_patterns = ["&&", ";", "|", "`", "$(", "${"]
    if any(pattern in decoded_command for pattern in forbidden_patterns):
        raise HTTPException(status_code=400, detail="Invalid characters in command.")
    

    unused_port = find_unused_port()
    if not unused_port:
        raise HTTPException(status_code=500, detail="Failed to find an unused port.")
    

    decoded_command = re.sub(r'-p (\d+):', f'-p {unused_port}:', decoded_command)
    

    try:
        subprocess.Popen(["./run_and_stop.sh", decoded_command])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute command: {e}")

    return {"message": "Command is running in the background with an unused port.", "unused_port": unused_port}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
