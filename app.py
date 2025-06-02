from flask import Flask, request, jsonify
import logging
import psycopg2
import os
import json
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
        phone_meta = metadata.get("phone_call", {})

        def safe_get(key):
            return collected.get(key, {}).get("value")

        values = {
            "conversation_id": call_data.get("conversation_id"),
            "agent_id": call_data.get("agent_id"),
            "zip_code": safe_get("zip_code"),
            "age": safe_get("age"),
            "household_size": safe_get("household_size"),
            "income": safe_get("income"),
            "insurance": safe_get("insurance"),
            "life_change": safe_get("life_change"),
            "qualified": safe_get("Qualified"),
            "willing_to_talk": safe_get("Willing_to_talk"),
            "first_name": safe_get("first_name"),
            "phone_number": safe_get("phone_number"),
            "call_successful": analysis.get("call_successful"),
            "call_duration_secs": metadata.get("call_duration_secs"),
            "call_sid": phone_meta.get("call_sid"),
            "external_number": phone_meta.get("external_number"),
            "agent_number": phone_meta.get("agent_number")
        }

        logging.info("📤 Extracted data: %s", values)
        insert_into_db(values)
        return jsonify({"status": "success"}), 200

    except Exception as e:
        logging.exception("❌ Webhook error")
        return jsonify({"status": "error", "message": str(e)}), 500

def insert_into_db(values):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO aca_responses (
                        conversation_id, agent_id, zip_code, age, household_size, income,
                        insurance, life_change, qualified, willing_to_talk, first_name,
                        phone_number, call_successful, call_duration_secs, call_sid,
                        external_number, agent_number
                    ) VALUES (
                        %(conversation_id)s, %(agent_id)s, %(zip_code)s, %(age)s, %(household_size)s,
                        %(income)s, %(insurance)s, %(life_change)s, %(qualified)s, %(willing_to_talk)s,
                        %(first_name)s, %(phone_number)s, %(call_successful)s, %(call_duration_secs)s,
                        %(call_sid)s, %(external_number)s, %(agent_number)s
                    )
                """, values)
            conn.commit()
    except Exception as e:
        logging.exception("❌ Database insert failed")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
