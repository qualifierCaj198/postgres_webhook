
from flask import Flask, request, jsonify
import logging
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'your_db'),
    'user': os.getenv('DB_USER', 'your_user'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', 5432),
}

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(force=True)
        logging.info("📥 Payload received at %s", datetime.utcnow().isoformat())

        call_data = data.get("data", {})
        metadata = call_data.get("metadata", {})
        analysis = call_data.get("analysis", {})
        collected = analysis.get("data_collection_results", {})

        transcript_list = call_data.get("transcript", [])
        transcript_text = "\n".join(
            f"{entry['role']}: {entry['message']}" for entry in transcript_list if entry.get("message")
        )
        call_summary = analysis.get("transcript_summary", "")

        phone_meta = metadata.get("phone_call", {})
        call_duration = metadata.get("call_duration_secs")
        termination_reason = metadata.get("termination_reason")
        call_successful = analysis.get("call_successful")

        voicemail_detected = any(
            "voicemail" in (entry.get("message", "") or "").lower()
            or "mailbox is full" in (entry.get("message", "") or "").lower()
            for entry in call_data.get("transcript", [])
            if entry.get("role") == "agent"
        )

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO responses (
                agent_id, conversation_id, call_sid, external_number, agent_number,
                first_name, zip_code, age, household_size, income,
                insurance, willing_to_talk, life_change, qualified,
                transcript, summary, call_duration_secs, call_successful,
                termination_reason, voicemail_detected
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            call_data.get("agent_id"),
            call_data.get("conversation_id"),
            phone_meta.get("call_sid"),
            phone_meta.get("external_number"),
            phone_meta.get("agent_number"),
            collected.get("first_name", {}).get("value"),
            collected.get("zip_code", {}).get("value"),
            collected.get("age", {}).get("value"),
            collected.get("household_size", {}).get("value"),
            collected.get("income", {}).get("value"),
            collected.get("insurance", {}).get("value"),
            collected.get("Willing_to_talk", {}).get("value"),
            collected.get("life_change", {}).get("value"),
            collected.get("Qualified", {}).get("value"),
            transcript_text,
            call_summary,
            call_duration,
            call_successful,
            termination_reason,
            voicemail_detected
        ))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.exception("❌ Error handling webhook")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
