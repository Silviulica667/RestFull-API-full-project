from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import requests
import datetime
import json
import os

app = FastAPI()

date = datetime.datetime.now().strftime('%Y-%m-%d')
zoom = 0.2
NASA_KEY = "vZUWYdZEZOlAvukKN3670Gm04P21o3ivNrLBj522"
API_KEY = "FCKHKMLU7XG6UQLZJKG6A6UND"

export_file_path = r"export.json"

@app.get("/")
def read_root():
    return FileResponse(os.path.join("..", "frontend", "index.html"))

@app.get("/image_url")
def get_image_url(long: float, lat: float):
    url = f"https://api.nasa.gov/planetary/earth/assets?lon={long}&lat={lat}&date={date}&dim={zoom}&api_key={NASA_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()  
        data = response.json()
        image_url = data['url']
        return JSONResponse(content={"url": image_url})
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/set_zoom")
async def set_zoom(request: Request):
    global zoom
    data = await request.json()
    zoom = data.get("zoom")
    return {"zoom": zoom}

@app.post("/set_lat")
async def set_lat(request: Request):
    global lat
    data = await request.json()
    lat = data.get("latitude")
    return {"latitude": lat}

@app.post("/set_long")
async def set_long(request: Request):
    global long
    data = await request.json()
    long = data.get("longitude")
    return {"longitude": long}

@app.post("/fetch_events")
def fetch_eonet_events():
    eonet_url = "https://eonet.gsfc.nasa.gov/api/v2.1/events?days=7"
    response = requests.get(eonet_url)
    response.raise_for_status() 

    data = response.json()
    events = data['events']
    print("Fetched events:", events)

    export_data = {
        "events": events
    }

    with open(export_file_path, 'w') as export_file:
        json.dump(export_data, export_file, indent=4)

    return JSONResponse(content={"events": events, "message": "Events saved to export.json"})

@app.get("/export.json")
def get_export_json():

    with open(export_file_path, 'r'):
        export_data = json.load(export_file_path)
    return JSONResponse(content=export_data)

@app.get("/extract_coordinates")
def extract_coordinates():
    with open(export_file_path, 'r') as export_file:
        export_data = json.load(export_file)
    
    coordinates = []
    for event in export_data["events"]:
        coordinates.append({
            "date": ["date"],
            "longitude": ["coordinates"][0],
            "latitude": ["coordinates"][1]
        })
    return JSONResponse(content={"coordinates": coordinates})


@app.get("/get_coordinates")
def get_coordinates(city: str):
    base_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/last1days/?key={API_KEY}&include=days&elements=tempmax,tempmin,temp"
    
    response = requests.get(base_url)
    response.raise_for_status()
    data = response.json()

    if "latitude" not in data or "longitude" not in data:
        return JSONResponse(content={"error": "City coordinates not found"}, status_code=404)

    city_coordinates = {
        "latitude": data["latitude"],
        "longitude": data["longitude"]
    }

    export_data = {
        "city": {
            "name": city,
            "coordinates": city_coordinates
        }
    }

    with open(export_file_path, 'w') as export_file:
        json.dump(export_data, export_file, indent=4)

    return JSONResponse(content=city_coordinates)

