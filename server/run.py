# server/run.py

import asyncio
import sys
import uvicorn

# --- THE CRITICAL FIX ---
# We apply the event loop policy fix here, at the very beginning,
# before Uvicorn or FastAPI even get imported and start their own loops.
# This guarantees that the correct policy is in place from the start.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# --- END FIX ---

# Now we can safely import our app
from main import app

if __name__ == "__main__":
    print("Starting ContextMAN server with custom runner...")
    # We programmatically tell uvicorn to run our 'app' instance.
    uvicorn.run(app, host="127.0.0.1", port=8000)