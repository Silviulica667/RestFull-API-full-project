import customtkinter as ctk
from tkinter import messagebox
import requests, random, datetime, webbrowser, os
import folium, matplotlib.pyplot as plt

ctk.set_appearance_mode("dark")  # "light", "dark", "system"
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("CarSense - Smart Vehicle Tracker")
root.geometry("1400x700")

CAR_SENSOR_TYPES = {
    "engine_temp":       ("°C", 70, 110),
    "coolant_temp":      ("°C", 60, 100),
    "oil_pressure":      ("bar", 1.0, 5.0),
    "battery_voltage":   ("V", 12.0, 14.8),
    "fuel_level":        ("%", 0, 100),
    "intake_air_temp":   ("°C", -10, 60),
}


COUNTRIES_COORDINATES = {
    "România": [(43.6, 27.0), (48.2, 21.2)],
    "Germania": [(47.3, 5.9), (55.1, 15.0)],
    "Franța":   [(42.3, -5.1), (51.1, 8.2)],
    "Italia":   [(36.6, 6.6), (47.1, 18.5)]
}

API_URL = "https://restfull-api-full-project-production.up.railway.app/senzori"

WEATHER_URL = "https://restfull-api-full-project-production.up.railway.app/senzori/{}/weather"

senzori_data = []

tabview = ctk.CTkTabview(root, width=1000, height=650)
tabview.pack(padx=0, pady=20, expand=True, fill="both")

main_tab = tabview.add("Senzori")
# map_tab = tabview.add("Hartă")  # opțional

# -------------------- Left Controls --------------------
left_frame = ctk.CTkFrame(main_tab, width=700)
left_frame.pack(side="left", fill="y", padx=10, pady=10)

sensors_scroll = ctk.CTkScrollableFrame(left_frame, width=700, height=400)
sensors_scroll.pack(pady=10, fill="both", expand=True)
sensor_buttons = []
selected_sensor_id = None


filter_tip = ctk.CTkComboBox(left_frame, values=[""] + list(CAR_SENSOR_TYPES.keys()), width=180)
filter_tip.pack(pady=5)
ctk.CTkButton(left_frame, text="Filtrează", command=lambda: refresh_list()).pack()

# -------------------- Right Controls --------------------
right_frame = ctk.CTkFrame(main_tab)
right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

entry_country = ctk.CTkComboBox(right_frame, values=list(COUNTRIES_COORDINATES.keys()))
entry_country.pack(pady=5)
entry_country.set("România")

entry_tip = ctk.CTkComboBox(right_frame, values=list(CAR_SENSOR_TYPES.keys()))
entry_tip.pack(pady=5)
entry_tip.set("engine_temp")


entry_locatie = ctk.CTkEntry(right_frame, placeholder_text="Locație")
entry_locatie.pack(pady=5)
entry_time = ctk.CTkEntry(right_frame)
entry_time.pack(pady=5)

entry_marca = ctk.CTkComboBox(right_frame, values=[], width=180)
entry_marca.pack(pady=5)

entry_marca.configure(command=lambda val: load_models_for_make(val))


def delete_selected_sensor():
    if selected_sensor_id is None:
        messagebox.showwarning("Ștergere", "Nu ai selectat niciun senzor.")
        return
    try:
        requests.delete(f"{API_URL}/{selected_sensor_id}").raise_for_status()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", f"Eroare la ștergere: {e}")


def update_time():
    entry_time.delete(0, 'end')
    entry_time.insert(0, datetime.datetime.now().isoformat(timespec="seconds"))
    root.after(1000, update_time)
update_time()

btn_frame = ctk.CTkFrame(right_frame)
btn_frame.pack(pady=10)

ctk.CTkButton(btn_frame, text="Adaugă", width=120, command=lambda: add_sensor()).pack(pady=2)
ctk.CTkButton(btn_frame, text="Modifică", width=120, command=lambda: update_sensor()).pack(pady=2)
ctk.CTkButton(btn_frame, text="Șterge", width=120, command=lambda: delete_selected_sensor()).pack(pady=2)
ctk.CTkButton(btn_frame, text="Istoric", width=120, command=lambda: show_history_plot()).pack(pady=2)
ctk.CTkButton(btn_frame, text="Harta toți", width=120, command=lambda: generate_map(False)).pack(pady=2)
ctk.CTkButton(btn_frame, text="Harta probleme", width=120, command=lambda: generate_map(True)).pack(pady=2)
ctk.CTkButton(btn_frame, text="Senzor pe hartă", width=120, command=lambda: show_selected_sensor_on_map()).pack(pady=2)


def refresh_list():
    global sensor_buttons, selected_sensor_id
    try:
        r = requests.get(API_URL)
        r.raise_for_status()
        data = r.json()
        senzori_data.clear()
        selected_sensor_id = None

        # Curăță frame-ul scrollabil
        for widget in sensors_scroll.winfo_children():
            widget.destroy()
        sensor_buttons.clear()

        selected_tip = filter_tip.get()
        for s in data:
            if selected_tip and s["tip"] != selected_tip:
                continue
            senzori_data.append(s)

            vehicul = s.get("vehicul", "")
            if "nicio variantă" in vehicul.lower():
                vehicul = "Necunoscut"

            text = (f"ID: {s['id']} | {s['tip']} = {s['valoare']} {s.get('unitate','')} "
                    f"| Vehicul: {vehicul} | Loc: {s['locatie']}")

            btn = ctk.CTkButton(sensors_scroll, text=text, width=360, anchor="w", fg_color="#2a2a2a",
                                command=lambda sid=s['id']: select_sensor_by_id(sid))
            btn.pack(pady=2)
            sensor_buttons.append(btn)
    except Exception as e:
        messagebox.showerror("Eroare", f"Eroare la refresh: {e}")

def select_sensor_by_id(sid):
    global selected_sensor_id
    selected_sensor_id = sid
    s = next((sensor for sensor in senzori_data if sensor["id"] == sid), None)
    if not s:
        return

    entry_tip.set(s["tip"])
    entry_locatie.delete(0, 'end')
    entry_locatie.insert(0, s["locatie"])
    entry_time.delete(0, 'end')
    entry_time.insert(0, s["time"])

    vehicul = s.get("vehicul", "")
    parts = vehicul.split(" ", 1)
    if len(parts) == 2:
        marca, model = parts
        entry_marca.set(marca)
        load_models_for_make(marca)
    else:
        entry_marca.set("Alege marcă")



def get_random_location(country):
    bounds = COUNTRIES_COORDINATES.get(country)
    if not bounds: return "Unknown"
    lat_min, lon_min = bounds[0]; lat_max, lon_max = bounds[1]
    lat = round(random.uniform(lat_min, lat_max), 5)
    lon = round(random.uniform(lon_min, lon_max), 5)
    try:
        r = requests.get("https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "CarSense-App"}).json()
        return r.get("address", {}).get("city") or r.get("display_name", f"{lat}, {lon}")
    except: return f"{lat}, {lon}"

def add_sensor():
    try:
        tip = entry_tip.get()
        unit, mn, mx = CAR_SENSOR_TYPES[tip]
        loc = get_random_location(entry_country.get())

        vehicul = f"{entry_marca.get()}"
        if "nicio variantă" in vehicul.lower():
            vehicul = entry_marca.get()

        data = {
            "tip": tip,
            "valoare": int(random.uniform(mn, mx)) if tip == "fuel_level" else round(random.uniform(mn, mx), 2),
            "locatie": loc,
            "vehicul": vehicul,
            "time": entry_time.get()
        }

        r = requests.post(API_URL, json=data)
        r.raise_for_status()
        response_data = r.json()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", str(e))


def load_makes():
    try:
        r = requests.get("https://carapi.app/api/makes")
        r.raise_for_status()
        data = r.json().get("data", [])

        makes = sorted({
            item["name"] for item in data
            if item.get("name") and "subscription required" not in item["name"].lower()
        })

        if makes:
            entry_marca.configure(values=list(makes))
            entry_marca.set(makes[0])
            load_models_for_make(makes[0])
        else:
            entry_marca.configure(values=["Nicio marcă disponibilă"])
            entry_marca.set("Nicio marcă disponibilă")
    except Exception as e:
        messagebox.showerror("Eroare", f"Nu s-au putut încărca mărcile: {e}")

# La începutul fișierului
model_cache = {}

def load_models_for_make(marca):
    try:
        if marca in model_cache:
            models = model_cache[marca]
        else:
            r = requests.get("https://carapi.app/api/models", params={"make": marca})
            r.raise_for_status()
            raw_models = r.json().get("data", [])
            models = sorted({
                item["name"] for item in raw_models
                if item.get("name") and "subscription required" not in item["name"].lower()
            })
            model_cache[marca] = models

    except Exception as e:
        messagebox.showerror("Eroare", f"Nu s-au putut încărca modelele: {e}")


def update_sensor():
    if selected_sensor_id is None:
        messagebox.showwarning("Modificare", "Selectează un senzor din listă mai întâi.")
        return
    try:
        sensor = next((s for s in senzori_data if s["id"] == selected_sensor_id), None)
        if not sensor:
            messagebox.showerror("Eroare", "Senzorul nu a fost găsit în listă.")
            return

        vehicul = f"{entry_marca.get()}"
        if "nicio variantă" in vehicul.lower():
            vehicul = entry_marca.get()

        updated_data = {
            "id": sensor["id"],
            "tip": entry_tip.get(),
            "valoare": sensor["valoare"],  # păstrăm valoarea originală
            "locatie": entry_locatie.get(),
            "vehicul": vehicul,
            "time": entry_time.get()
        }

        r = requests.put(f"{API_URL}/{sensor['id']}", json=updated_data)

        r.raise_for_status()
        refresh_list()
        messagebox.showinfo("Succes", f"Senzorul #{sensor['id']} a fost actualizat.")
    except Exception as e:
        messagebox.showerror("Eroare", f"Eroare la modificare: {e}")



def show_history_plot():
    if not senzori_data: return
    s = senzori_data[-1]  # Ultimul senzor din listă
    tip = s['tip']; valoare = float(s['valoare'])
    unit = CAR_SENSOR_TYPES.get(tip, ("",))[0]
    valori = [round(valoare + random.uniform(-5, 5), 2) for _ in range(10)]
    timp = [f"T-{i}" for i in range(10, 0, -1)]
    plt.figure(figsize=(8, 4))
    plt.plot(timp, valori, marker='o')
    plt.title(f"Istoric pentru '{tip}'")
    plt.xlabel("Timp"); plt.ylabel(f"Valoare ({unit})")
    plt.grid(True); plt.tight_layout(); plt.show()

def generate_map(only_problems=False):
    m = folium.Map(location=[45.9, 24.9], zoom_start=6)
    coduri = {
        0: "Cer senin",
        1: "Parțial noros",
        2: "Noros",
        3: "Înnorat",
        45: "Ceață",
        48: "Ceață cu depuneri de gheață",
        51: "Burniță slabă",
        53: "Burniță moderată",
        55: "Burniță intensă",
        56: "Burniță înghețată slabă",
        57: "Burniță înghețată intensă",
        61: "Ploaie slabă",
        63: "Ploaie moderată",
        65: "Ploaie intensă",
        66: "Ploaie înghețată slabă",
        67: "Ploaie înghețată intensă",
        71: "Ninsoare slabă",
        73: "Ninsoare moderată",
        75: "Ninsoare abundentă",
        77: "Fulgi de zăpadă",
        80: "Averse slabe",
        81: "Averse moderate",
        82: "Averse puternice",
        85: "Averse de ninsoare slabă",
        86: "Averse de ninsoare intensă",
        95: "Furtună",
        96: "Furtună cu grindină slabă",
        99: "Furtună cu grindină severă"
    }

    limits = {
        "engine_temp":     lambda v: v > 105,
        "coolant_temp":    lambda v: v > 95,
        "oil_pressure":    lambda v: v < 1.5,
        "battery_voltage": lambda v: v < 12.2,
        "fuel_level":      lambda v: v < 10,
        "intake_air_temp": lambda v: v > 50,
    }

    added = 0
    for s in senzori_data:
        if only_problems and not limits.get(s["tip"], lambda _: False)(s["valoare"]):
            continue
        try:
            geo = requests.get("https://nominatim.openstreetmap.org/search",
                params={"q": s["locatie"], "format": "json", "limit": 1},
                headers={"User-Agent": "CarSense-App"}).json()
            if not geo:
                continue
            lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
            w = requests.get(WEATHER_URL.format(s["id"])).json()
            cod = w.get("weathercode", "-")

            vehicul = s.get('vehicul', '')
            if "nicio variantă" in vehicul.lower():
                vehicul = "Necunoscut"

            popup = folium.Popup(f"""
            <div style='width: 260px; font-size: 13px; line-height: 1.5; white-space: normal;'>
            <b>Tip senzor:</b> {s['tip']}<br>
            <b>Valoare:</b> {s['valoare']} {s.get('unitate','')}<br>
            <b>Vehicul:</b> {vehicul}<br>
            <b>Locație:</b> {s['locatie']}<br>
            <b>Data:</b> {s['time']}<br>
            <b>Vreme:</b> {coduri.get(cod, 'necunoscut')} (cod {cod})<br>
            <b>Temp. exterioară:</b> {w.get("temperature_2m", "N/A")} °C
            </div>
            """, max_width=300)




            color = "red" if limits.get(s["tip"], lambda _: False)(s["valoare"]) else "green"
            folium.Marker([lat, lon], popup=popup, icon=folium.Icon(color=color)).add_to(m)
            added += 1
        except:
            continue
    if added == 0:
        messagebox.showwarning("Harta", "Nicio locație validă.")
        return
    m.save("map.html")
    webbrowser.open(f"file://{os.path.abspath('map.html')}")

def show_selected_sensor_on_map():
    if selected_sensor_id is None:
        messagebox.showwarning("Harta", "Nu ai selectat niciun senzor.")
        return

    sensor = next((s for s in senzori_data if s["id"] == selected_sensor_id), None)
    if not sensor:
        return

    loc = sensor.get("locatie", "")
    try:
        geo = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": loc, "format": "json", "limit": 1},
            headers={"User-Agent": "CarSense-App"}).json()
        if not geo:
            messagebox.showerror("Eroare", "Locația nu a putut fi geocodificată.")
            return

        lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])

        # Obține vremea
        w = requests.get(WEATHER_URL.format(sensor["id"])).json()
        cod = w.get("weathercode", "-")

        coduri = {
            0: "Cer senin", 1: "Parțial noros", 2: "Noros", 3: "Înnorat",
            45: "Ceață", 48: "Ceață cu depuneri", 51: "Burniță slabă", 53: "Burniță moderată", 55: "Burniță puternică",
            56: "Burniță înghețată slabă", 57: "Burniță înghețată intensă", 61: "Ploaie slabă", 63: "Ploaie moderată",
            65: "Ploaie puternică", 66: "Ploaie înghețată slabă", 67: "Ploaie înghețată intensă",
            71: "Ninsoare slabă", 73: "Ninsoare moderată", 75: "Ninsoare puternică", 77: "Fulgi de zăpadă",
            80: "Averse slabe", 81: "Averse moderate", 82: "Averse puternice",
            85: "Averse de ninsoare slabă", 86: "Averse de ninsoare intensă",
            95: "Furtună", 96: "Furtună cu grindină", 99: "Furtună severă"
        }

        vehicul = sensor.get('vehicul', 'Necunoscut')
        if "nicio variantă" in vehicul.lower():
            vehicul = "Necunoscut"

        popup = folium.Popup(f"""
            <div style='width: 260px; font-size: 13px; line-height: 1.5; white-space: normal;'>
            <b>Tip senzor:</b> {sensor['tip']}<br>
            <b>Valoare:</b> {sensor['valoare']} {sensor.get('unitate','')}<br>
            <b>Vehicul:</b> {vehicul}<br>
            <b>Locație:</b> {sensor['locatie']}<br>
            <b>Data:</b> {sensor['time']}<br>
            <b>Vreme:</b> {coduri.get(cod, 'necunoscut')} (cod {cod})<br>
            <b>Temp. exterioară:</b> {w.get("temperature_2m", "N/A")} °C
            </div>
        """, max_width=300)

        m = folium.Map(location=[lat, lon], zoom_start=12)
        folium.Marker([lat, lon], popup=popup, icon=folium.Icon(color="blue")).add_to(m)
        m.save("selected.html")
        webbrowser.open(f"file://{os.path.abspath('selected.html')}")
    except Exception as e:
        messagebox.showerror("Eroare", f"Eroare la afișarea pe hartă: {e}")



refresh_list()
load_makes()
root.mainloop()