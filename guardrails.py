import re
import json
import logging
from datetime import datetime

logger = logging.getLogger("guardrails")
logger.setLevel(logging.INFO)
_fh = logging.FileHandler("guardrail_log.jsonl")
_fh.setLevel(logging.INFO)
logger.addHandler(_fh)

# ── G1: Input Guardrail ─────────────────────────────────────────────────────

BLOCKED_PATTERNS = [
    r"ignore (previous|all|your) instructions?",
    r"you are now",
    r"act as (a|an)? (different|unrestricted|evil|jailbreak)",
    r"forget (your|all) (rules?|instructions?|guidelines?)",
    r"(prompt injection|jailbreak|bypass)",
]

OFF_TOPIC_KEYWORDS = [
    "password", "credit card", "ssn", "social security",
    "hack", "exploit", "malware", "sql injection",
]

MAX_QUERY_LENGTH = 500

def validate_input(query: str) -> dict:
    """
    G1 — Validates user query before it enters the RAG pipeline.
    Returns: {"allowed": bool, "reason": str}
    """
    # Length check
    if len(query.strip()) == 0:
        return {"allowed": False, "reason": "Query is empty."}

    if len(query) > MAX_QUERY_LENGTH:
        return {"allowed": False, "reason": f"Query too long. Max {MAX_QUERY_LENGTH} characters."}

    # Prompt injection / jailbreak detection
    lower_query = query.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lower_query):
            _log_event("INPUT_BLOCKED", query, reason="Prompt injection attempt")
            return {"allowed": False, "reason": "Query contains disallowed instructions."}

    # Off-topic sensitive keyword check
    for kw in OFF_TOPIC_KEYWORDS:
        if kw in lower_query:
            _log_event("INPUT_FLAGGED", query, reason=f"Sensitive keyword: {kw}")
            return {"allowed": False, "reason": "Query contains sensitive or off-topic content."}

    return {"allowed": True, "reason": "ok"}


# ── G2: Context Confidence Guardrail ────────────────────────────────────────

MIN_CONTEXT_SCORE = 0.3   # Pinecone similarity score threshold
MIN_CHUNKS_REQUIRED = 1

def validate_context(matched_chunks: list) -> dict:
    """
    G2 — Checks if retrieved context is relevant enough to answer.
    Pinecone returns chunks as dicts with a 'score' field.
    Returns: {"sufficient": bool, "reason": str}
    """
    if not matched_chunks or len(matched_chunks) < MIN_CHUNKS_REQUIRED:
        return {
            "sufficient": False,
            "reason": "I couldn't find relevant information in the uploaded document to answer this question."
        }

    # Check top chunk relevance score (Pinecone cosine similarity)
    top_score = matched_chunks[0].get("score", 0)
    if top_score < MIN_CONTEXT_SCORE:
        return {
            "sufficient": False,
            "reason": f"The document doesn't seem to contain relevant information for this query (confidence: {top_score:.2f})."
        }

    return {"sufficient": True, "reason": "ok"}


# ── G3: Output Guardrail ─────────────────────────────────────────────────────

PII_PATTERNS = {
    "email":   r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone":   r"\b(\+\d{1,3}[\s.-])?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
    "aadhar":  r"\b\d{4}\s?\d{4}\s?\d{4}\b",  # India-specific
}

HALLUCINATION_PHRASES = [
    "as of my knowledge cutoff",
    "i don't have access to",
    "i cannot browse the internet",
    "as a language model",
    "i was trained on",
    "my training data",
]

MAX_RESPONSE_LENGTH = 1500

def validate_output(response: str, query: str) -> dict:
    """
    G3 — Validates LLM response before sending to user.
    Returns: {"safe": bool, "response": str, "flags": list}
    """
    flags = []
    cleaned = response

    # PII scrubbing
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, cleaned)
        if matches:
            cleaned = re.sub(pattern, f"[{pii_type.upper()} REDACTED]", cleaned)
            flags.append(f"PII_SCRUBBED:{pii_type}")

    # Hallucination signal detection
    lower_resp = cleaned.lower()
    for phrase in HALLUCINATION_PHRASES:
        if phrase in lower_resp:
            flags.append("HALLUCINATION_SIGNAL")
            cleaned = cleaned + "\n\n⚠️ Note: This response may contain information beyond the uploaded document."
            break

    # Length trim
    if len(cleaned) > MAX_RESPONSE_LENGTH:
        cleaned = cleaned[:MAX_RESPONSE_LENGTH] + "... [truncated for safety]"
        flags.append("TRUNCATED")

    # Empty or useless response check
    if len(cleaned.strip()) < 20:
        return {
            "safe": False,
            "response": "I was unable to generate a useful response. Please try rephrasing your question.",
            "flags": ["EMPTY_RESPONSE"]
        }

    if flags:
        _log_event("OUTPUT_FLAGGED", query, reason=str(flags), response_preview=cleaned[:100])

    return {"safe": True, "response": cleaned, "flags": flags}


# ── G4: Observability Logger ─────────────────────────────────────────────────

def _log_event(event_type: str, query: str, reason: str = "", response_preview: str = ""):
    """Appends a structured JSON log entry to guardrail_log.jsonl"""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "query_preview": query[:80],
        "reason": reason,
        "response_preview": response_preview
    }
    logger.info(json.dumps(entry))

def log_successful_interaction(query: str, response: str, flags: list):
    """Logs clean interactions for monitoring and audit."""
    _log_event(
        "INTERACTION_OK",
        query,
        reason=f"flags={flags}",
        response_preview=response[:100]
    )