from fastapi import APIRouter, HTTPException
import os
import httpx
import asyncio

router = APIRouter()

# Simple in-memory circuit breaker
LLM_FAILURES = 0
LLM_CIRCUIT_OPEN_UNTIL = 0
MAX_FAILURES = int(os.getenv('LLM_CIRCUIT_MAX_FAILURES', '5'))
CIRCUIT_COOLDOWN = int(os.getenv('LLM_CIRCUIT_COOLDOWN_MS', '60000'))
MAX_RETRIES = int(os.getenv('LLM_MAX_RETRIES', '2'))


@router.post('/invoke')
async def invoke(body: dict):
    global LLM_FAILURES, LLM_CIRCUIT_OPEN_UNTIL
    prompt = body.get('prompt', '')
    LLM_API_URL = os.getenv('LLM_API_URL')
    LLM_API_KEY = os.getenv('LLM_API_KEY')
    if not LLM_API_URL:
        return {'text': f'Local LLM stub: {str(prompt)[:180]}'}

    # Fast-fail if circuit open
    if LLM_CIRCUIT_OPEN_UNTIL and LLM_CIRCUIT_OPEN_UNTIL > int(asyncio.get_event_loop().time() * 1000):
        raise HTTPException(status_code=503, detail='LLM provider temporarily unavailable (circuit open)')

    timeout_sec = float(os.getenv('LLM_TIMEOUT_SEC', '15'))
    last_exc = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                headers = {'Content-Type': 'application/json'}
                if LLM_API_KEY:
                    headers['Authorization'] = f'Bearer {LLM_API_KEY}'
                r = await client.post(LLM_API_URL, json={'prompt': prompt}, headers=headers)
                r.raise_for_status()
                LLM_FAILURES = 0
                return r.json()
        except httpx.TimeoutException as e:
            last_exc = e
            # timeout — retryable
        except Exception as e:
            last_exc = e
            # Treat server 5xx as retryable
            if isinstance(e, httpx.HTTPStatusError) and 500 <= e.response.status_code < 600:
                pass
            else:
                # Non-retryable
                break
        # backoff before next attempt
        await asyncio.sleep(0.2 * (2 ** attempt))

    # If we reach here, it's a failure
    LLM_FAILURES += 1
    if LLM_FAILURES >= MAX_FAILURES:
        LLM_CIRCUIT_OPEN_UNTIL = int(asyncio.get_event_loop().time() * 1000) + CIRCUIT_COOLDOWN
    raise HTTPException(status_code=502, detail=str(last_exc))
