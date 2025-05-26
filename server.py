from flask import Flask, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# PostgreSQL connection
DATABASE_URL = "postgresql://postgres:zzwgEzqxGdneoILQCXgLfwqLwiwYKqIm@shuttle.proxy.rlwy.net:46988/railway"

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

CAR_SENSOR_TYPES = {
    "temperature": {"unit": "°C", "min": -40, "max": 150},
    "speed": {"unit": "km/h", "min": 0, "max": 300},
    "rpm": {"unit": "RPM", "min": 0, "max": 8000},
    "fuel": {"unit": "%", "min": 0, "max": 100},
    "battery": {"unit": "V", "min": 11.5, "max": 14.8}
}

# Ensure table exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS senzori (
        id INTEGER PRIMARY KEY,
        tip TEXT NOT NULL,
        valoare REAL NOT NULL,
        locatie TEXT NOT NULL,
        time TEXT NOT NULL
    );
""")
conn.commit()

@app.route("/senzori", methods=["GET"])
def get_sensors():
    cursor.execute("SELECT * FROM senzori;")
    rows = cursor.fetchall()
    sensors = [{
        "id": r[0], "tip": r[1], "valoare": r[2], "locatie": r[3], "time": r[4]
    } for r in rows]
    return jsonify(sensors), 200

@app.route("/senzori", methods=["POST"])
def add_sensor():
    data = request.json
    if data["tip"] not in CAR_SENSOR_TYPES:
        return jsonify({"error": "Tip de senzor invalid"}), 400

    conf = CAR_SENSOR_TYPES[data["tip"]]
    if not (conf["min"] <= data["valoare"] <= conf["max"]):
        return jsonify({"error": "Valoare în afara limitelor"}), 400

    try:
        cursor.execute("SELECT 1 FROM senzori WHERE id = %s;", (data["id"],))
        exists = cursor.fetchone()
        if exists:
            cursor.execute("""
                UPDATE senzori
                SET tip=%s, valoare=%s, locatie=%s, time=%s
                WHERE id=%s;
            """, (data["tip"], data["valoare"], data["locatie"], data["time"], data["id"]))
            conn.commit()
            return jsonify({"message": "Senzor actualizat"}), 203
        else:
            cursor.execute("""
                INSERT INTO senzori (id, tip, valoare, locatie, time)
                VALUES (%s, %s, %s, %s, %s);
            """, (data["id"], data["tip"], data["valoare"], data["locatie"], data["time"]))
            conn.commit()
            return jsonify({"message": "Senzor adăugat"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/senzori/<int:id>", methods=["DELETE"])
def delete_sensor(id):
    cursor.execute("DELETE FROM senzori WHERE id = %s;", (id,))
    conn.commit()
    return jsonify({"message": "Senzor șters"}), 202

@app.route("/senzori/tipuri", methods=["GET"])
def get_types():
    return jsonify(CAR_SENSOR_TYPES), 200

if __name__ == "__main__":
    app.run(debug=True)
