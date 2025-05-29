# server.py
from flask import Flask, request, jsonify
import psycopg2
import os
import requests
from datetime import datetime

app = Flask(__name__)

# Conexiune PostgreSQL (Railway)
DATABASE_URL = os.getenv("DATABASE_URL",
    "postgresql://postgres:pDSmlXNxsFYsBnNkbryBUxaorrMjdVbs@centerbeam.proxy.rlwy.net:49284/railway"
)
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Tipuri de senzori auto
CAR_SENSOR_TYPES = {
    "engine_temp":       {"unit": "°C",  "min": 70,  "max": 110},
    "coolant_temp":      {"unit": "°C",  "min": 60,  "max": 100},
    "oil_pressure":      {"unit": "bar", "min": 1.0, "max": 5.0},
    "battery_voltage":   {"unit": "V",   "min": 12.0,"max": 14.8},
    "fuel_level":        {"unit": "%",   "min": 0,   "max": 100},
    "intake_air_temp":   {"unit": "°C",  "min": -10, "max": 60}
}


cursor.execute("""
CREATE TABLE IF NOT EXISTS senzori2 (
    id SERIAL PRIMARY KEY,
    tip TEXT NOT NULL,
    valoare REAL NOT NULL,
    locatie TEXT NOT NULL,
    vehicul TEXT,
    time TEXT NOT NULL
);
""")



cursor.execute("""
ALTER TABLE senzori2
ADD COLUMN IF NOT EXISTS vehicul TEXT;
""")
conn.commit()


@app.route("/senzori", methods=["GET"])
def get_sensors():
    cursor.execute("SELECT id, tip, valoare, locatie, vehicul, time FROM senzori2;")
    rows = cursor.fetchall()
    sensors = []
    for r in rows:
        tip = r[1]
        unit = CAR_SENSOR_TYPES.get(tip, {}).get("unit", "")
        sensors.append({
            "id":       r[0],
            "tip":      tip,
            "valoare":  r[2],
            "unitate":  unit,
            "locatie":  r[3],
            "vehicul":  r[4],
            "time":     r[5]
        })
    return jsonify(sensors), 200


@app.route("/senzori", methods=["POST"])
def add_sensor():
    data = request.json or {}
    tip = data.get("tip")
    valoare = data.get("valoare")
    if tip not in CAR_SENSOR_TYPES:
        return jsonify({"error": "Tip de senzor invalid"}), 400
    conf = CAR_SENSOR_TYPES[tip]
    if valoare is None or not (conf["min"] <= valoare <= conf["max"]):
        return jsonify({"error": f"Valoare în afara limitelor ({conf['min']}–{conf['max']})"}), 400

    try:
        cursor.execute("""
            INSERT INTO senzori2 (tip, valoare, locatie, vehicul, time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            tip, valoare,
            data.get("locatie"), data.get("vehicul"), data.get("time")
        ))
        new_id = cursor.fetchone()[0]
        conn.commit()
        return jsonify({"message": "Senzor adăugat", "id": new_id}), 201
    except Exception as e:
        conn.rollback()
        print("Eroare la adăugare senzor:", e)  # Asta ajută la debugging
        return jsonify({"error": str(e)}), 500



@app.route("/senzori/<int:sensor_id>", methods=["DELETE"])
def delete_sensor(sensor_id):
    try:
        cursor.execute("DELETE FROM senzori2 WHERE id = %s;", (sensor_id,))
        conn.commit()
        return jsonify({"message": "Senzor șters"}), 202
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/senzori/tipuri", methods=["GET"])
def get_types():
    return jsonify(CAR_SENSOR_TYPES), 200


@app.route("/geocode", methods=["GET"])
def geocode():
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    if not lat or not lon:
        return jsonify({"error": "Trebuie specificați parametri lat și lon"}), 400
    resp = requests.get(
        "https://nominatim.openstreetmap.org/reverse",
        params={"format": "jsonv2", "lat": lat, "lon": lon, "accept-language": "ro"},
        headers={"User-Agent": "CarSense-App"}
    )
    data = resp.json()
    addr = data.get("address", {})
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
    return jsonify({"lat": float(lat), "lon": float(lon), "city": city}), 200


@app.route("/senzori/<int:sensor_id>/weather", methods=["GET"])
def sensor_weather(sensor_id):

    cursor.execute("SELECT locatie, time FROM senzori2 WHERE id = %s;", (sensor_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Senzor nu există"}), 404
    locatie, timestr = row

    geo = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": locatie, "format": "jsonv2", "limit": 1},
        headers={"User-Agent": "CarSense-App"}
    ).json()
    if not geo:
        return jsonify({"error": "Localitate necunoscută"}), 400
    lat, lon = geo[0]["lat"], geo[0]["lon"]

    dt = datetime.fromisoformat(timestr)
    date = dt.date().isoformat()
    hour_str = f"{dt.hour:02d}:00"

    params = {
        "latitude": lat, "longitude": lon,
        "start_date": date, "end_date": date,
        "hourly": "temperature_2m,relativehumidity_2m,precipitation,weathercode,winddirection_10m,windspeed_10m",
        "timezone": "Europe/Bucharest"
    }
    wresp = requests.get("https://api.open-meteo.com/v1/forecast", params=params)
    if wresp.status_code != 200:
        return jsonify({"error": "Eroare la API-ul meteo"}), 502
    hourly = wresp.json().get("hourly", {})

    times = hourly.get("time", [])
    try:
        idx = times.index(f"{date}T{hour_str}")
    except ValueError:
        return jsonify({"error": "Ora nu e disponibilă în răspuns"}), 502

    return jsonify({
        "sensor_id":        sensor_id,
        "location":         locatie,
        "datetime":         timestr,
        "latitude":         lat,
        "longitude":        lon,
        "temperature_2m":   hourly["temperature_2m"][idx],
        "humidity":         hourly["relativehumidity_2m"][idx],
        "precipitation":    hourly["precipitation"][idx],
        "weathercode":      hourly["weathercode"][idx],
        "winddirection_10m":hourly["winddirection_10m"][idx],
        "windspeed_10m":    hourly["windspeed_10m"][idx]
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


