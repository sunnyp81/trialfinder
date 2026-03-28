"""
Rewrite clinical trial eligibility criteria into plain English using Claude API.

Estimated cost: ~$0.002 per trial x N trials
Usage: python scripts/rewrite_eligibility.py

Requires ANTHROPIC_API_KEY in .env file.
"""

import json
import os
import sqlite3
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DB_PATH = Path(__file__).parent / "data" / "trials.db"
BATCH_SIZE = 25
DELAY_BETWEEN_BATCHES = 1.0
MAX_RETRIES = 3

SYSTEM_PROMPT = """You are a patient advocate helping seriously ill people understand clinical \
trials. Your job is to rewrite dense medical eligibility criteria into \
language a worried parent or patient can understand at an 8th-grade reading \
level.

Rules:
- Replace all jargon with plain English. If a medical term is unavoidable, \
define it in parentheses immediately after.
- Replace lab value ranges with descriptions: 'normal kidney function' \
not 'eGFR ≥ 60 mL/min', 'not severely anaemic' not 'Hgb > 8 g/dL'.
- Use "you" and "your" to speak directly to the patient.
- Maximum 10 bullets per section. Pick the most important criteria.
- Start bullet points with a short bold keyword: \
**Age**: you must be between 18 and 65.

Respond ONLY with valid JSON in this exact shape, no markdown, no preamble:
{
  "can_join": ["bullet 1", "bullet 2", ...],
  "cannot_join": ["bullet 1", "bullet 2", ...],
  "plain_summary": "Two sentence plain English summary starting with 'This trial is testing...'"
}"""


def rewrite_trial(client: anthropic.Anthropic, raw_eligibility: str) -> dict | None:
    """Call Claude to rewrite eligibility criteria. Returns parsed JSON or None."""
    if not raw_eligibility or len(raw_eligibility.strip()) < 20:
        return None

    message = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Rewrite these eligibility criteria:\n\n{raw_eligibility}"
        }]
    )

    response_text = message.content[0].text.strip()
    tokens_in = message.usage.input_tokens
    tokens_out = message.usage.output_tokens

    # Try to parse JSON
    try:
        parsed = json.loads(response_text)
        if "can_join" in parsed and "cannot_join" in parsed and "plain_summary" in parsed:
            return {
                "can_join": parsed["can_join"],
                "cannot_join": parsed["cannot_join"],
                "plain_summary": parsed["plain_summary"],
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            }
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    if "```" in response_text:
        import re
        match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if "can_join" in parsed and "cannot_join" in parsed:
                    return {
                        "can_join": parsed["can_join"],
                        "cannot_join": parsed["cannot_join"],
                        "plain_summary": parsed.get("plain_summary", ""),
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                    }
            except json.JSONDecodeError:
                pass

    return None


def process_batch(client: anthropic.Anthropic, conn: sqlite3.Connection, trials: list[tuple]):
    """Process a batch of trials."""
    total_tokens = 0
    success = 0

    for nct_id, raw_eligibility, brief_summary in trials:
        retries = 0
        while retries < MAX_RETRIES:
            try:
                result = rewrite_trial(client, raw_eligibility)
                if result:
                    conn.execute("""
                        UPDATE trials SET
                            can_join = ?,
                            cannot_join = ?,
                            plain_summary = ?,
                            plain_eligibility = 'done'
                        WHERE nct_id = ?
                    """, (
                        json.dumps(result["can_join"]),
                        json.dumps(result["cannot_join"]),
                        result["plain_summary"],
                        nct_id,
                    ))
                    total_tokens += result["tokens_in"] + result["tokens_out"]
                    success += 1
                    print(f"  ✓ {nct_id} ({result['tokens_in']}+{result['tokens_out']} tokens)")
                else:
                    # No eligibility to rewrite, mark as done with brief_summary
                    conn.execute("""
                        UPDATE trials SET
                            plain_eligibility = 'skipped',
                            plain_summary = ?
                        WHERE nct_id = ?
                    """, (brief_summary or "", nct_id))
                    print(f"  - {nct_id} skipped (no eligibility criteria)")
                break
            except anthropic.APIError as e:
                retries += 1
                if retries < MAX_RETRIES:
                    print(f"  ! {nct_id} API error (retry {retries}/{MAX_RETRIES}): {e}")
                    time.sleep(2 * retries)
                else:
                    conn.execute(
                        "INSERT INTO error_log (trial_id, error_type, error_message) VALUES (?, ?, ?)",
                        (nct_id, "api_error", str(e))
                    )
                    print(f"  ✗ {nct_id} failed after {MAX_RETRIES} retries")
            except Exception as e:
                conn.execute(
                    "INSERT INTO error_log (trial_id, error_type, error_message) VALUES (?, ?, ?)",
                    (nct_id, "unexpected_error", str(e))
                )
                print(f"  ✗ {nct_id} unexpected error: {e}")
                break

    conn.commit()
    return success, total_tokens


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY not set. Add it to .env file.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    client = anthropic.Anthropic(api_key=api_key)

    # Get trials that haven't been rewritten yet
    cursor = conn.execute("""
        SELECT nct_id, raw_eligibility, brief_summary
        FROM trials
        WHERE plain_eligibility IS NULL
        ORDER BY nct_id
    """)
    pending = cursor.fetchall()

    total = len(pending)
    if total == 0:
        print("All trials already rewritten. Nothing to do.")
        conn.close()
        return

    estimated_cost = total * 0.002
    print(f"Rewriting eligibility for {total} trials")
    print(f"Estimated cost: ~${estimated_cost:.2f}")
    print(f"Batch size: {BATCH_SIZE}, delay: {DELAY_BETWEEN_BATCHES}s")
    print()

    total_success = 0
    total_tokens = 0
    batch_num = 0

    for i in range(0, total, BATCH_SIZE):
        batch_num += 1
        batch = pending[i:i + BATCH_SIZE]
        print(f"Batch {batch_num} ({i+1}-{min(i+BATCH_SIZE, total)} of {total}):")

        success, tokens = process_batch(client, conn, batch)
        total_success += success
        total_tokens += tokens

        if i + BATCH_SIZE < total:
            time.sleep(DELAY_BETWEEN_BATCHES)

    # Estimated cost (Sonnet 4.5: $3/M input, $15/M output)
    est_cost = (total_tokens * 0.000005)  # rough average
    print(f"\nDone! {total_success}/{total} trials rewritten")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Estimated cost: ~${est_cost:.4f}")

    # Check for errors
    cursor = conn.execute("SELECT COUNT(*) FROM error_log")
    errors = cursor.fetchone()[0]
    if errors:
        print(f"Errors logged: {errors} (check error_log table)")

    conn.close()


if __name__ == "__main__":
    main()
