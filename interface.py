import tkinter as tk
from tkinter import messagebox, ttk
from PIL import ImageTk
import requests, io, random, datetime, webbrowser
import folium, os
import matplotlib.pyplot as plt
import json

API_URL = "http://127.0.0.1:5000/senzori"
WEATHER_URL = "http://127.0.0.1:5000/senzori/{}/weather"

CAR_SENSOR_TYPES = {
    "temperature": ("°C", -40, 150),
    "speed":       ("km/h", 0, 300),
    "rpm":         ("RPM", 0, 8000),
    "fuel":        ("%", 0, 100),
    "battery":     ("V", 11.5, 14.8)
}

COUNTRIES_COORDINATES = {
    "România": [(43.6, 27.0), (48.2, 21.2)],
    "Germania": [(47.3, 5.9), (55.1, 15.0)],
    "Franța":   [(42.3, -5.1), (51.1, 8.2)],
    "Italia":   [(36.6, 6.6), (47.1, 18.5)]
}

root = tk.Tk()
root.title("CarSense - Smart Vehicle Tracker")
notebook = ttk.Notebook(root)
frame_main = ttk.Frame(notebook)
frame_map = ttk.Frame(notebook)
notebook.add(frame_main, text="Senzori")
notebook.pack(expand=True, fill="both")

senzori_data = []
sensors_list = tk.Listbox(frame_main, width=100)
sensors_list.pack(pady=5)


entry_country = ttk.Combobox(frame_main, values=list(COUNTRIES_COORDINATES.keys()))
entry_country.current(0); entry_country.pack()

entry_tip = ttk.Combobox(frame_main, values=list(CAR_SENSOR_TYPES.keys())); entry_tip.current(0); entry_tip.pack()
entry_locatie = tk.Entry(frame_main); entry_locatie.pack()
entry_vehicul = tk.Entry(frame_main); entry_vehicul.pack()
entry_time = tk.Entry(frame_main); entry_time.pack()
vehicle_info_label = tk.Label(frame_main, text="Detalii vehicul: "); vehicle_info_label.pack()

def update_time():
    entry_time.delete(0, tk.END)
    entry_time.insert(0, datetime.datetime.now().isoformat(timespec="seconds"))
    root.after(1000, update_time)
update_time()

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

def refresh_list():
    global senzori_data
    try:
        r = requests.get(API_URL); r.raise_for_status()
        data = r.json()
        senzori_data.clear()
        sensors_list.delete(0, tk.END)

        selected_tip = filter_tip.get()
        for s in data:
            if selected_tip and s["tip"] != selected_tip:
                continue
            senzori_data.append(s)
            sensors_list.insert(tk.END,
                f"ID:{s['id']} | {s['tip']} = {s['valoare']} {s.get('unitate','')} "
                f"| Loc: {s['locatie']} | Vehicul: {s.get('vehicul','')} | Timp: {s['time']}")
    except Exception as e:
        messagebox.showerror("Eroare", f"Eroare la refresh_list: {e}")

filter_frame = tk.Frame(frame_main); filter_frame.pack(pady=5)

filter_tip = ttk.Combobox(filter_frame, values=[""] + list(CAR_SENSOR_TYPES.keys()), width=20)
filter_tip.set("")  # opțional, poți seta "temperature" implicit
filter_tip.pack(side=tk.LEFT, padx=5)

tk.Button(filter_frame, text="Filtrează", command=refresh_list).pack(side=tk.LEFT, padx=5)


def on_select_sensor(event):
    sel = sensors_list.curselection()
    if not sel: return
    s = senzori_data[sel[0]]
    entry_tip.set(s.get("tip",""))
    entry_locatie.delete(0, tk.END); entry_locatie.insert(0, s.get("locatie",""))
    entry_vehicul.delete(0, tk.END); entry_vehicul.insert(0, s.get("vehicul",""))
    entry_time.delete(0, tk.END); entry_time.insert(0, s.get("time",""))

def add_sensor():
    try:
        tip = entry_tip.get(); unit, mn, mx = CAR_SENSOR_TYPES[tip]
        loc = get_random_location(entry_country.get())
        data = {
            "id": random.randint(1000,9999),
            "tip": tip,
            "valoare": round(random.uniform(mn, mx), 2),
            "locatie": loc,
            "vehicul": entry_vehicul.get(),
            "time": entry_time.get()
        }
        requests.post(API_URL, json=data).raise_for_status()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def update_sensor():
    sel = sensors_list.curselection()
    if not sel: return
    s = senzori_data[sel[0]]
    try:
        data = {
            "id": s["id"],
            "tip": entry_tip.get(),
            "valoare": s["valoare"],
            "locatie": entry_locatie.get(),
            "vehicul": entry_vehicul.get(),
            "time": entry_time.get()
        }
        requests.post(API_URL, json=data).raise_for_status()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def show_weather():
    sel = sensors_list.curselection()
    if not sel: return
    sid = senzori_data[sel[0]]["id"]
    try:
        w = requests.get(WEATHER_URL.format(sid)).json()
        coduri = {
            0: "Cer senin", 1: "Parțial noros", 2: "Noros", 3: "Înnorat",
            45: "Ceață", 51: "Burniță", 61: "Ploaie", 71: "Ninsoare", 80: "Averse", 95: "Furtună"
        }
        msg = (
            f"Vreme în {w['location']}:\n"
            f" • Temperatură: {w['temperature_2m']}°C\n"
            f" • Umiditate: {w['humidity']}%\n"
            f" • Vânt: {w['windspeed_10m']} km/h\n"
            f" • Cod meteo: {w['weathercode']} - {coduri.get(w['weathercode'], 'necunoscut')}"
        )
        messagebox.showinfo("Vreme senzor", msg)
    except Exception as e:
        messagebox.showerror("Eroare vreme", str(e))

def show_history_plot():
    sel = sensors_list.curselection()
    if not sel: return
    s = senzori_data[sel[0]]
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
    coduri = {0: "Cer senin", 1: "Parțial noros", 2: "Noros", 3: "Înnorat", 95: "Furtună"}
    limits = {
        "temperature": lambda v: v < -20 or v > 100,
        "speed":       lambda v: v > 250,
        "rpm":         lambda v: v > 6000,
        "fuel":        lambda v: v < 10,
        "battery":     lambda v: v < 12
    }
    added = 0
    for s in senzori_data:
        if only_problems and not limits.get(s["tip"], lambda _: False)(s["valoare"]): continue
        try:
            geo = requests.get("https://nominatim.openstreetmap.org/search",
                params={"q": s["locatie"], "format": "json", "limit": 1},
                headers={"User-Agent": "CarSense-App"}).json()
            if not geo: continue
            lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
            w = requests.get(WEATHER_URL.format(s["id"])).json()
            cod = w.get("weathercode", "-")
            popup = (
                f"<b>{s['tip']}</b> = {s['valoare']} {s.get('unitate','')}<br>"
                f"{s.get('vehicul','')} la {s['locatie']}<br>"
                f"{s['time']}<br>"
                f"Cod meteo: {cod} - {coduri.get(cod, 'necunoscut')}"
            )
            color = "red" if limits.get(s["tip"], lambda _: False)(s["valoare"]) else "green"
            folium.Marker([lat, lon], popup=popup,
                          icon=folium.Icon(color=color)).add_to(m)
            added += 1
        except: continue
    if added == 0:
        messagebox.showwarning("Harta", "Nicio locație validă.")
        return
    m.save("map.html"); webbrowser.open(f"file://{os.path.abspath('map.html')}")

def show_selected_sensor_on_map():
    sel = sensors_list.curselection()
    if not sel: return
    s = senzori_data[sel[0]]
    loc = s.get("locatie", "")
    geo = requests.get("https://nominatim.openstreetmap.org/search",
        params={"q": loc, "format": "json", "limit": 1},
        headers={"User-Agent": "CarSense-App"}).json()
    if not geo: return
    lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
    m = folium.Map(location=[lat, lon], zoom_start=10)
    popup = f"{s['tip']} @ {s['locatie']} = {s['valoare']} {s.get('unitate','')}"
    folium.Marker([lat, lon], popup=popup).add_to(m)
    m.save("selected.html"); webbrowser.open(f"file://{os.path.abspath('selected.html')}")

#----------------------

btn_frame = tk.Frame(frame_main); btn_frame.pack(pady=5)
for txt, cmd in [
    ("Adaugă", add_sensor),
    ("Modifică", update_sensor),
    ("Istoric", show_history_plot),
    ("Harta toți senzorii", lambda: generate_map(False)),
    ("Harta probleme", lambda: generate_map(True)),
    ("Senzor selectat", show_selected_sensor_on_map)
]:
    tk.Button(btn_frame, text=txt, width=18, command=cmd).pack(side=tk.LEFT, padx=2)


# tk.Button(frame_map, text="Toți senzorii", command=lambda: generate_map(False)).pack(pady=3)
# tk.Button(frame_map, text="Doar probleme", command=lambda: generate_map(True)).pack(pady=3)
# tk.Button(frame_map, text="Senzor selectat", command=show_selected_sensor_on_map).pack(pady=3)

sensors_list.bind("<<ListboxSelect>>", on_select_sensor)
refresh_list()
root.mainloop()
