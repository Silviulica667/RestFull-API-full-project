
# interface.py
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import requests, io, random, datetime

API_URL     = "http://127.0.0.1:5000/senzori"
GEOCODE_URL = "http://127.0.0.1:5000/geocode"
WEATHER_URL = "http://127.0.0.1:5000/senzori/{}/weather"

CAR_SENSOR_TYPES = {
    "temperature": ("\u00b0C", -40, 150),
    "speed":       ("km/h", 0,   300),
    "rpm":         ("RPM", 0,    8000),
    "fuel":        ("%", 0,      100),
    "battery":     ("V", 11.5,  14.8)
}

senzori_data = []

def refresh_list():
    global senzori_data
    try:
        resp = requests.get(API_URL); resp.raise_for_status()
        sensors_list.delete(0, tk.END)
        senzori_data = resp.json()
        for s in senzori_data:
            sensors_list.insert(tk.END,
                f"{s['id']}, {s['tip']}, {s['valoare']} {s.get('unitate','')}," \
                f" {s['locatie']}, {s.get('vehicul','')}," \
                f" {s['time']}"
            )
    except Exception as e:
        messagebox.showerror("Eroare", f"Nu s-au putut încărca senzorii: {e}")

def on_select_sensor(event):
    sel = sensors_list.curselection()
    if not sel: return
    s = senzori_data[sel[0]]
    entry_tip.set(s.get("tip",""))
    entry_locatie.delete(0, tk.END)
    entry_locatie.insert(0, s.get("locatie",""))
    entry_vehicul.delete(0, tk.END)
    entry_vehicul.insert(0, str(s.get("vehicul","")))
    entry_time.delete(0, tk.END)
    entry_time.insert(0, s.get("time",""))

def add_sensor():
    try:
        tip = entry_tip.get()
        unit, mn, mx = CAR_SENSOR_TYPES.get(tip, ("",0,1))
        data = {
            "id": random.randint(1000,9999),
            "tip": tip,
            "valoare": round(random.uniform(mn,mx),2),
            "locatie": entry_locatie.get(),
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
        sid = int(sensors_list.get(sel[0]).split(",")[0].strip())
        requests.delete(f"{API_URL}/{sid}")
        refresh_list()

def update_time():
    entry_time.delete(0, tk.END)
    entry_time.insert(0, datetime.datetime.now().isoformat(timespec="seconds"))
    root.after(1000, update_time)

def show_map_image():
    city = entry_locatie.get().strip()
    if not city:
        messagebox.showwarning("Lipsă", "Introduceți o locație.")
        return

    try:
        # 1. Geocoding cu Nominatim
        geo_resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "jsonv2", "limit": 1},
            headers={"User-Agent": "CarSense-App"}
        )
        geo_resp.raise_for_status()
        geo = geo_resp.json()
        if not geo:
            raise Exception("Locație necunoscută")
        lat = float(geo[0]["lat"])
        lon = float(geo[0]["lon"])

        # 2. Detalii locale cu GeoNames
        # Înregistrare gratuită la http://www.geonames.org/login
        GEONAMES_USERNAME = "demo"  # înlocuiește cu username-ul tău
        gn_resp = requests.get(
            "http://api.geonames.org/findNearbyPlaceNameJSON",
            params={"lat": lat, "lng": lon, "username": GEONAMES_USERNAME}
        )
        gn_resp.raise_for_status()
        gn = gn_resp.json().get("geonames", [])
        if gn:
            details = gn[0]
            name       = details.get("name", city)
            region     = details.get("adminName1", "-")
            country    = details.get("countryName", "-")
            population = details.get("population", "-")
            postal     = details.get("postalcode", "-")
        else:
            name, region, country, population, postal = city, "-", "-", "-", "-"

        # 3. Construiește URL Harta Yandex
        map_url = (
            f"https://static-maps.yandex.ru/1.x/"
            f"?ll={lon:.5f},{lat:.5f}&z=12&size=400,400&l=map&"
            f"pt={lon:.5f},{lat:.5f},pm2rdm"
        )
        img_data = requests.get(map_url).content
        img = Image.open(io.BytesIO(img_data)).resize((400, 400))
        img_tk = ImageTk.PhotoImage(img)

        # 4. Fereastră nouă și afișare
        win = tk.Toplevel(root)
        win.title(f"Hartă și detalii pentru {city}")

        canvas = tk.Canvas(win, width=400, height=400)
        canvas.pack()
        canvas.create_image(0, 0, anchor="nw", image=img_tk)
        win.image = img_tk  # păstrăm referința

        # 5. Afișăm coordonate și detalii sub hartă
        info = (
            f"Nume localitate: {name}\n"
            f"Regiune: {region}\n"
            f"Țară: {country}\n"
            f"Populație: {population}\n"
            f"Cod poștal: {postal}\n"
            f"Coordonate: {lat:.5f}, {lon:.5f}"
        )
        lbl = tk.Label(win, text=info, justify="left", font=("Arial", 10))
        lbl.pack(pady=10)

    except Exception as e:
        messagebox.showerror("Eroare hartă & detalii", str(e))

def show_weather():
    sel = sensors_list.curselection()
    if not sel:
        messagebox.showwarning("Lipsă", "Selectează un senzor pentru vreme.")
        return
    sid = senzori_data[sel[0]]["id"]
    try:
        r = requests.get(WEATHER_URL.format(sid))
        r.raise_for_status()
        w = r.json()

        # Descrieri pentru coduri meteo
        weather_codes = {
            0: "Cer senin", 1: "Înnorat ușor", 2: "Înnorat", 3: "Cer acoperit",
            45: "Ceață", 48: "Ceață cu depunere", 51: "Burniță slabă",
            61: "Ploaie slabă", 63: "Ploaie moderată", 65: "Ploaie puternică",
            71: "Ninsoare slabă", 73: "Ninsoare moderată", 80: "Averse ușoare",
            95: "Furtună", 96: "Furtună cu grindină slabă", 99: "Furtună cu grindină puternică"
        }

        msg = (
            f"Vreme la {w['datetime']} în {w['location']}:\n"
            f" • Temperatură: {w['temperature_2m']} °C\n"
            f" • Umiditate: {w['humidity']} %\n"
            f" • Precipitații: {w['precipitation']} mm\n"
            f" • Cod meteo: {w['weathercode']} ({weather_codes.get(w['weathercode'], 'Necunoscut')})\n"
            f" • Vânt: {w['windspeed_10m']} km/h la {w['winddirection_10m']}°"
        )
        messagebox.showinfo(f"Vreme pentru senzor {sid}", msg)
    except Exception as e:
        messagebox.showerror("Eroare vreme", str(e))

# === GUI ===
root = tk.Tk()
root.title("CarSense - Interfață Extinsă")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

tk.Label(frame, text="Senzori în baza de date:").pack()
sensors_list = tk.Listbox(frame, width=80)
sensors_list.pack(pady=5)
sensors_list.bind("<<ListboxSelect>>", on_select_sensor)

entry_tip = ttk.Combobox(frame, values=list(CAR_SENSOR_TYPES.keys()))
entry_tip.current(0); tk.Label(frame, text="Tip senzor").pack(); entry_tip.pack()
entry_locatie = tk.Entry(frame); tk.Label(frame, text="Locație").pack(); entry_locatie.pack()
entry_vehicul = tk.Entry(frame); tk.Label(frame, text="Vehicul").pack(); entry_vehicul.pack()
entry_time = tk.Entry(frame); tk.Label(frame, text="Timp").pack(); entry_time.pack()

update_time()

btn_frame = tk.Frame(frame)
btn_frame.pack(pady=5)
for txt, cmd in [
    ("Adaugă senzor", add_sensor),
    ("Șterge senzor", delete_sensor),
    ("Modifică senzor", update_sensor),
    ("Hartă locație", show_map_image),
    ("Vreme senzor", show_weather)
]:
    tk.Button(btn_frame, text=txt, width=15, command=cmd).pack(side=tk.LEFT, padx=2)

refresh_list()
root.mainloop()

