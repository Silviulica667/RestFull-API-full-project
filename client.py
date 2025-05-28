import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import requests, io, random, datetime, webbrowser
import folium, os
import matplotlib.pyplot as plt

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

senzori_data = []
root = tk.Tk()
root.title("CarSense - Smart Vehicle Tracker")
notebook = ttk.Notebook(root)
frame_main = ttk.Frame(notebook)
frame_map = ttk.Frame(notebook)
notebook.add(frame_main, text="Senzori")
notebook.add(frame_map, text="Hartă")
notebook.pack(expand=True, fill="both")

tk.Label(frame_main, text="Senzori în baza de date:").pack()
sensors_list = tk.Listbox(frame_main, width=100)
sensors_list.pack(pady=5)

entry_country = ttk.Combobox(frame_main, values=list(COUNTRIES_COORDINATES.keys()))
entry_country.current(0)
tk.Label(frame_main, text="Țara pentru coordonate aleatorii").pack()
entry_country.pack()

def get_random_location(country):
    bounds = COUNTRIES_COORDINATES.get(country)
    if not bounds: return "Unknown"
    lat_min, lon_min = bounds[0]
    lat_max, lon_max = bounds[1]
    lat = round(random.uniform(lat_min, lat_max), 5)
    lon = round(random.uniform(lon_min, lon_max), 5)
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "CarSense-App"}).json()
        return resp.get("address", {}).get("city") or resp.get("display_name", f"{lat}, {lon}")
    except:
        return f"{lat}, {lon}"

def refresh_list():
    global senzori_data
    try:
        resp = requests.get(API_URL); resp.raise_for_status()
        senzori_data = resp.json()
        sensors_list.delete(0, tk.END)
        for s in senzori_data:
            sensors_list.insert(tk.END,
                f"ID:{s['id']} | {s['tip']} = {s['valoare']} {s.get('unitate','')} | Loc: {s['locatie']} | Vehicul: {s.get('vehicul','')} | Timp: {s['time']}")
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

entry_tip = ttk.Combobox(frame_main, values=list(CAR_SENSOR_TYPES.keys())); entry_tip.current(0)
tk.Label(frame_main, text="Tip senzor").pack(); entry_tip.pack()
entry_locatie = tk.Entry(frame_main); tk.Label(frame_main, text="Locație").pack(); entry_locatie.pack()
entry_vehicul = tk.Entry(frame_main); tk.Label(frame_main, text="Vehicul").pack(); entry_vehicul.pack()
entry_time = tk.Entry(frame_main); tk.Label(frame_main, text="Timp").pack(); entry_time.pack()

def update_time():
    entry_time.delete(0, tk.END)
    entry_time.insert(0, datetime.datetime.now().isoformat(timespec="seconds"))
    root.after(1000, update_time)
update_time()

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
        tip = entry_tip.get()
        unit, mn, mx = CAR_SENSOR_TYPES.get(tip, ("", 0, 1))
        country = entry_country.get()
        location_name = get_random_location(country)
        data = {
            "id": random.randint(1000,9999),
            "tip": tip,
            "valoare": round(random.uniform(mn, mx), 2),
            "locatie": location_name,
            "vehicul": entry_vehicul.get(),
            "time": entry_time.get()
        }
        r = requests.post(API_URL, json=data); r.raise_for_status()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def update_sensor():
    sel = sensors_list.curselection()
    if not sel:
        messagebox.showerror("Eroare", "Selectează un senzor.")
        return
    idx = sel[0]; sid = senzori_data[idx]["id"]
    data = {
        "id": sid,
        "tip": entry_tip.get(),
        "valoare": senzori_data[idx]["valoare"],
        "locatie": entry_locatie.get(),
        "vehicul": entry_vehicul.get(),
        "time": entry_time.get()
    }
    try:
        r = requests.post(API_URL, json=data); r.raise_for_status()
        refresh_list()
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def delete_sensor():
    sel = sensors_list.curselection()
    if sel:
        sid = senzori_data[sel[0]]['id']
        requests.delete(f"{API_URL}/{sid}")
        refresh_list()

def show_weather():
    sel = sensors_list.curselection()
    if not sel:
        messagebox.showwarning("Lipsă", "Selectează un senzor pentru vreme.")
        return
    sid = senzori_data[sel[0]]["id"]
    try:
        r = requests.get(WEATHER_URL.format(sid)); r.raise_for_status()
        w = r.json()
        msg = (
            f"Vreme la {w['datetime']} în {w['location']}:\n"
            f" • Temperatură: {w['temperature_2m']} °C\n"
            f" • Umiditate: {w['humidity']} %\n"
            f" • Precipitații: {w['precipitation']} mm\n"
            f" • Cod meteo: {w['weathercode']}\n"
            f" • Vânt: {w['windspeed_10m']} km/h la {w['winddirection_10m']}°"
        )
        messagebox.showinfo(f"Vreme pentru senzor {sid}", msg)
    except Exception as e:
        messagebox.showerror("Eroare vreme", str(e))

def show_history_plot():
    sel = sensors_list.curselection()
    if not sel:
        messagebox.showwarning("Istoric", "Selectează un senzor.")
        return
    s = senzori_data[sel[0]]
    tip = s['tip']; valoare = float(s['valoare'])
    unit = CAR_SENSOR_TYPES.get(tip, ("",))[0]
    valori = [round(valoare + random.uniform(-5, 5), 2) for _ in range(10)]
    timp = [f"T-{i}" for i in range(10, 0, -1)]
    plt.figure(figsize=(8, 4))
    plt.plot(timp, valori, marker='o')
    plt.title(f"Istoric valori pentru senzorul '{tip}'")
    plt.xlabel("Timp (simulat)")
    plt.ylabel(f"Valoare ({unit})")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def show_selected_sensor_on_map():
    sel = sensors_list.curselection()
    if not sel:
        messagebox.showwarning("Selectează", "Selectează un senzor din listă.")
        return
    s = senzori_data[sel[0]]
    loc = s.get("locatie", "")
    try:
        geo = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": loc, "format": "json", "limit": 1},
            headers={"User-Agent": "CarSense-App"}).json()
        if not geo: return
        lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
        m = folium.Map(location=[lat, lon], zoom_start=10)
        popup = (
            f"<b>Tip:</b> {s['tip']}<br><b>Valoare:</b> {s['valoare']} {s.get('unitate','')}<br>"
            f"<b>Vehicul:</b> {s.get('vehicul','')}<br><b>Locație:</b> {loc}<br><b>Timp:</b> {s['time']}<br>"
        )
        w = requests.get(WEATHER_URL.format(s["id"]))
        if w.status_code == 200:
            wj = w.json()
            codes = {0: "Cer senin", 1: "Parțial noros", 2: "Noros", 3: "Înnorat", 95: "Furtună"}
            popup += f"<b>Cod meteo:</b> {wj.get('weathercode')} - {codes.get(wj.get('weathercode'), 'necunoscut')}<br>"
        folium.Marker([lat, lon], popup=folium.Popup(popup, max_width=300)).add_to(m)
        m.save("selected_sensor_map.html")
        webbrowser.open(f"file://{os.path.abspath('selected_sensor_map.html')}")
    except Exception as e:
        messagebox.showerror("Eroare hartă", str(e))

btn_frame = tk.Frame(frame_main); btn_frame.pack(pady=5)
for txt, cmd in [
    ("Adaugă senzor", add_sensor),
    ("Șterge senzor", delete_sensor),
    ("Modifică senzor", update_sensor),
    ("Vreme senzor", show_weather),
    ("Istoric senzor", show_history_plot)
]:
    tk.Button(btn_frame, text=txt, width=18, command=cmd).pack(side=tk.LEFT, padx=2)

tk.Button(frame_map, text="Toți senzorii", command=lambda: generate_map(False)).pack(pady=5)
tk.Button(frame_map, text="Doar probleme", command=lambda: generate_map(True)).pack(pady=5)
tk.Button(frame_map, text="Locația senzorului selectat", command=show_selected_sensor_on_map).pack(pady=5)

def generate_map(only_problems=False):
    m = folium.Map(location=[45.9432, 24.9668], zoom_start=6)
    SENSOR_LIMITS = {
        "temperature": lambda v: v < -20 or v > 100,
        "speed":       lambda v: v > 250,
        "rpm":         lambda v: v > 6000,
        "fuel":        lambda v: v < 10,
        "battery":     lambda v: v < 12
    }
    weather_codes = {
        0: "Cer senin", 1: "Parțial noros", 2: "Noros", 3: "Înnorat complet",
        45: "Ceață", 48: "Ceață cu chiciură", 51: "Burniță", 61: "Ploaie",
        71: "Ninsoare", 80: "Averse", 95: "Furtună", 96: "Furtună cu grindină", 99: "Furtună puternică"
    }
    added = 0
    for s in senzori_data:
        loc = s.get("locatie", "")
        try:
            geo = requests.get("https://nominatim.openstreetmap.org/search",
                params={"q": loc, "format": "json", "limit": 1},
                headers={"User-Agent": "CarSense-App"}).json()
            if not geo: continue
            lat, lon = float(geo[0]["lat"]), float(geo[0]["lon"])
            val = s["valoare"]; tip = s["tip"]
            problema = SENSOR_LIMITS.get(tip, lambda x: False)(val)
            if only_problems and not problema: continue
            popup = (
                f"<b>Tip:</b> {tip}<br><b>Valoare:</b> {val} {s.get('unitate','')}<br>"
                f"<b>Vehicul:</b> {s.get('vehicul','')}<br><b>Locație:</b> {loc}<br><b>Timp:</b> {s['time']}<br>"
            )
            weather = {}
            try:
                w = requests.get(WEATHER_URL.format(s["id"]))
                if w.status_code == 200: weather = w.json()
            except: pass
            if weather:
                cod = weather.get("weathercode", "-")
                popup += f"<b>Cod meteo:</b> {cod} - {weather_codes.get(cod, 'necunoscut')}<br>"
            color = "red" if problema else "green"
            folium.Marker([lat, lon], popup=folium.Popup(popup, max_width=300),
                          tooltip=f"{tip} @ {loc}", icon=folium.Icon(color=color)).add_to(m)
            added += 1
        except: continue
    if added == 0:
        messagebox.showwarning("Harta", "Nicio locație validă.")
        return
    m.save("sensors_map.html")
    webbrowser.open(f"file://{os.path.abspath('sensors_map.html')}")

sensors_list.bind("<<ListboxSelect>>", on_select_sensor)
refresh_list()
root.mainloop()
