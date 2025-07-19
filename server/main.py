# server/main.py

import os
import asyncio
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv
import groq

# --- Custom Imports ---
from browser_use import Agent
from browser_use.llm import ChatGroq

# Note: The critical asyncio fix for Windows is handled in the `run.py` script.

# Load environment variables from the .env file
load_dotenv()

# --- App and Client Configuration ---
app = FastAPI(
    title="ContextMAN Core API",
    description="An API for parsing web context and synthesizing structured prompts.",
    version="1.2.0", # Bump version for hardening fixes
)

# --- Centralized Configuration for Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = "mixtral-8x7b-32768"

# A simple check to ensure the API key is available
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set. Please create a .env file.")

# Configure the main ASYNCHRONOUS Groq client for the /synthesize endpoint.
client = groq.AsyncGroq(
    api_key=GROQ_API_KEY,
)

# --- Data Models ---
class ParseRequest(BaseModel):
    url: HttpUrl

class SynthesizeRequest(BaseModel):
    purpose: str
    parsed_context: str
    user_code: str | None = None


# --- API Endpoints ---
@app.get("/ping", summary="Health Check")
async def read_root():
    """A simple endpoint to check if the server is running."""
    return {"status": "ok", "message": f"ContextMAN server is running on Groq with model: {MODEL_NAME}"}


@app.post("/parse", summary="Parse a URL for Context")
async def parse_url(request: ParseRequest):
    """Receives a URL, uses a focused AI agent on Groq to browse it, and extracts content."""
    print(f"Received request to parse URL: {request.url}")

    # HARDENED PROMPT: This prompt is more restrictive to prevent the agent
    # from navigating away or performing unintended actions.
    parsing_task = (
        f"You are a web scraping assistant. Your ONLY job is to extract text from the provided URL: {request.url}. "
        "DO NOT navigate to any other URLs. DO NOT use search. "
        "Your primary goal is to extract the full user-assistant conversation from the page. "
        "Identify each turn of the conversation clearly, separating user and assistant roles. "
        "If there are code blocks within the conversation, ensure they are included and properly formatted using markdown code fences (```). "
        "If the page does not contain a conversation, return the main text content of the page. "
        "Return only the final extracted text as a single string."
    )

    try:
        # Configure the browser_use Agent to use Groq.
        groq_llm = ChatGroq(
            model=MODEL_NAME,
            api_key=GROQ_API_KEY,
            temperature=0.0,
        )

        agent = Agent(
            task=parsing_task,
            llm=groq_llm,
        )
        # Run the agent to perform the browsing and extraction
        result = await agent.run()

        # ROBUST ERROR CHECK: `if not result:` correctly handles None, empty strings "", etc.
        if not result:
            print("ERROR: Agent failed to produce a result or returned empty.")
            raise HTTPException(status_code=500, detail="The browser agent failed to extract content. Check server logs.")

        print("Parsing successful.")
        return {"parsed_content": result}
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to parse URL: {str(e)}")


@app.post("/synthesize", summary="Synthesize Context into a Prompt")
async def synthesize_context(request: SynthesizeRequest):
    """
    Takes parsed context and a user's purpose, then uses an LLM on Groq
    to generate a structured, portable prompt.
    """
    print(f"Received request to synthesize for purpose: {request.purpose}")

    system_prompt = """You are an expert AI assistant named ContextMAN. Your job is to take a user's goal, a messy block of context (like a chat history), and optional user-provided code, and synthesize them into a single, perfectly structured, portable prompt that can be used with any advanced AI model.

Follow these rules precisely:
1.  Start with a clear heading `### CONTEXT BRIEF ###`.
2.  State the user's ultimate goal clearly under a `**Goal:**` heading.
3.  Include a `**Key Information from Context:**` section where you concisely summarize the most important findings and takeaways from the provided chat history.
4.  If the user provided their own code, include it under a `**User-Provided Code:**` section, inside a proper markdown code block. If no code is provided, state 'N/A'.
5.  Finally, create a `---` separator and provide a `**Suggested Prompt:**` that clearly and directly tells the next AI what to do based on all the assembled context. This prompt should be ready to be copy-pasted.
"""

    user_code_section = f"```\n{request.user_code}\n```" if request.user_code else "N/A"

    user_message = f"""Here is the information to synthesize:

**User's Goal:**
{request.purpose}

**Messy Context / Chat History:**
{request.parsed_context}

**User's Code (if any):**
{user_code_section}
"""
    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.5,
        )
        final_prompt = response.choices[0].message.content
        print("Synthesis successful.")
        return {"synthesized_prompt": final_prompt}
    except Exception as e:
        print(f"An unexpected error occurred during synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to synthesize context: {str(e)}")