import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
import requests
import random
import datetime
import io

API_URL = "http://127.0.0.1:5000/senzori"

CAR_SENSOR_TYPES = {
    "temperature": ("\u00b0C", -40, 150),
    "speed": ("km/h", 0, 300),
    "rpm": ("RPM", 0, 8000),
    "fuel": ("%", 0, 100),
    "battery": ("V", 11.5, 14.8)
}

senzori_data = []

def refresh_list():
    global senzori_data
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            sensors_list.delete(0, tk.END)
            senzori_data = response.json()
            for s in senzori_data:
                sensors_list.insert(tk.END, f"{s['id']}, {s['tip']}, {s['valoare']} {s.get('unitate', '')}, {s['locatie']}, {s.get('vehicul', '')}, {s['time']}")
    except:
        messagebox.showerror("Eroare", "Nu s-au putut încărca senzorii.")

def on_select_sensor(event):
    selection = sensors_list.curselection()
    if selection:
        index = selection[0]
        sensor = senzori_data[index]
        entry_tip.set(sensor.get("tip", ""))
        entry_locatie.delete(0, tk.END)
        entry_locatie.insert(0, sensor.get("locatie", ""))
        entry_vehicul.delete(0, tk.END)
        entry_vehicul.insert(0, sensor.get("vehicul", "necunoscut"))
        entry_time.delete(0, tk.END)
        entry_time.insert(0, sensor.get("time", ""))

def add_sensor():
    try:
        tip = entry_tip.get()
        unitate, min_val, max_val = CAR_SENSOR_TYPES.get(tip, ("", 0, 100))
        valoare = round(random.uniform(min_val, max_val), 2)

        data = {
            "id": random.randint(1000, 9999),
            "tip": tip,
            "valoare": valoare,
            "unitate": unitate,
            "locatie": entry_locatie.get(),
            "vehicul": entry_vehicul.get(),
            "time": entry_time.get()
        }

        response = requests.post(API_URL, json=data)
        if response.status_code in [201, 203]:
            refresh_list()
        else:
            msg = response.json().get("error", "Eroare necunoscută")
            messagebox.showerror("Eroare", msg)
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def update_sensor():
    selection = sensors_list.curselection()
    if not selection:
        messagebox.showerror("Eroare", "Selectează un senzor pentru modificare.")
        return

    try:
        index = selection[0]
        sensor_id = senzori_data[index]["id"]
        tip = entry_tip.get()
        unitate, _, _ = CAR_SENSOR_TYPES.get(tip, ("", 0, 100))
        data = {
            "tip": tip,
            "valoare": senzori_data[index]["valoare"],
            "unitate": unitate,
            "locatie": entry_locatie.get(),
            "vehicul": entry_vehicul.get(),
            "time": entry_time.get()
        }
        response = requests.put(f"{API_URL}/{sensor_id}", json=data)
        if response.status_code in [200, 204]:
            refresh_list()
        else:
            messagebox.showerror("Eroare", f"{response.status_code} - {response.text}")
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def delete_sensor():
    selected = sensors_list.curselection()
    if selected:
        sensor_id = int(sensors_list.get(selected[0]).split(",")[0].strip())
        requests.delete(f"{API_URL}/{sensor_id}")
        refresh_list()

def update_time():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry_time.delete(0, tk.END)
    entry_time.insert(0, now)
    root.after(1000, update_time)

def show_map_image():
    city = entry_locatie.get()
    try:
        geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
        resp = requests.get(geo_url, headers={"User-Agent": "CarSense-App"})
        data = resp.json()[0]
        lat, lon = float(data["lat"]), float(data["lon"])

        image_url = f"https://static-maps.yandex.ru/1.x/?ll={lon},{lat}&z=12&size=400,400&l=map&pt={lon},{lat},pm2rdm"
        img_data = requests.get(image_url).content

        img = Image.open(io.BytesIO(img_data))
        img = img.resize((400, 400))
        img_tk = ImageTk.PhotoImage(img)

        win = tk.Toplevel(root)
        win.title(f"Hartă {city}")
        tk.Label(win, image=img_tk).pack()
        win.image = img_tk
    except Exception as e:
        messagebox.showerror("Eroare", str(e))

def show_weather(at_time=None):
    city = entry_locatie.get()
    try:
        geo_url = f"https://nominatim.openstreetmap.org/search?q={city}&format=json&limit=1"
        resp = requests.get(geo_url, headers={"User-Agent": "CarSense-App"})
        data = resp.json()[0]
        lat, lon = float(data["lat"]), float(data["lon"])

        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,windspeed_10m,weathercode,winddirection_10m&timezone=auto"
        meteo_data = requests.get(url).json()

        temps = meteo_data.get("hourly", {})
        if not temps:
            raise ValueError("Date meteo indisponibile")

        temp = temps["temperature_2m"][0]
        wind = temps["windspeed_10m"][0]
        direction = temps["winddirection_10m"][0]
        code = temps["weathercode"][0]
        at_time = temps["time"][0]

        weather_codes = {
            0: "Cer senin", 1: "Înnorat ușor", 2: "Înnorat", 3: "Cer acoperit",
            45: "Ceață", 48: "Ceață cu depunere", 51: "Burniță slabă", 53: "Burniță moderată", 55: "Burniță puternică",
            61: "Ploaie slabă", 63: "Ploaie moderată", 65: "Ploaie puternică",
            71: "Ninsoare slabă", 73: "Ninsoare moderată", 75: "Ninsoare abundentă",
            80: "Averse ușoare", 81: "Averse moderate", 82: "Averse puternice",
            95: "Furtună", 96: "Furtună cu grindină slabă", 99: "Furtună cu grindină puternică"
        }

        condition = weather_codes.get(code, "Cod necunoscut")

        message = (
            f"Temperatură: {temp} °C\n"
            f"Vânt: {wind} km/h (direcție: {direction}°)\n"
            f"Stare meteo: {condition} (cod {code})\n"
            f"Ora raportării: {at_time}"
        )
        messagebox.showinfo(f"Vremea în {city}", message)
    except Exception as e:
        messagebox.showerror("Eroare vreme", str(e))

# === GUI ===
root = tk.Tk()
root.title("CarSense - Interfață Extinsă")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Senzori în baza de date:").pack()
sensors_list = tk.Listbox(frame, width=80)
sensors_list.pack(pady=5)
sensors_list.bind("<<ListboxSelect>>", on_select_sensor)

tk.Label(frame, text="Tip senzor").pack()
entry_tip = ttk.Combobox(frame, values=list(CAR_SENSOR_TYPES.keys()))
entry_tip.current(0)
entry_tip.pack()

tk.Label(frame, text="Locație").pack()
entry_locatie = tk.Entry(frame)
entry_locatie.pack()

tk.Label(frame, text="Vehicul").pack()
entry_vehicul = tk.Entry(frame)
entry_vehicul.pack()

tk.Label(frame, text="Timp").pack()
entry_time = tk.Entry(frame)
entry_time.pack()

update_time()

tk.Button(frame, text="Adaugă senzor", command=add_sensor).pack(pady=5)
tk.Button(frame, text="Șterge senzor", command=delete_sensor).pack(pady=5)
tk.Button(frame, text="Hartă locație", command=show_map_image).pack(pady=5)
tk.Button(frame, text="Vreme locație", command=lambda: show_weather(None)).pack(pady=5)
tk.Button(frame, text="Modifică senzor", command=update_sensor).pack(pady=5)

refresh_list()
root.mainloop()
