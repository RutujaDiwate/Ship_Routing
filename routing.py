import pandas as pd
import math
from queue import PriorityQueue
import folium


# Load weather data
weather_data = pd.read_csv('weather_data.csv') 
depth_data = pd.read_csv('depth_data.csv')

# Clean datasets (drop NaN values, normalize coordinates, etc.)
weather_data = weather_data.dropna()
depth_data = depth_data.dropna()

# Convert coordinates into a graph format
# This step will depend on how you model the sea routes in the graph


start_lat = float(input("Enter starting port latitude: "))
start_lon = float(input("Enter starting port longitude: "))
destination_lat = float(input("Enter destination port latitude: "))
destination_lon = float(input("Enter destination port longitude: "))
ship_weight = float(input("Enter ship weight: "))


# Haversine formula to calculate distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of Earth in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Cost function considering distance, weather, and depth
def calculate_cost(current, neighbor, weather, depth, ship_weight):
    distance = haversine(current[0], current[1], neighbor[0], neighbor[1])
    weather_penalty = 100 if weather == 'storm' else 50 if weather == 'high_wind' else 10
    depth_penalty = 100 if depth < ship_weight else 50 if depth < 1.5 * ship_weight else 0
    return distance + weather_penalty + depth_penalty




def a_star_algorithm(graph, start, goal, weather_data, depth_data, ship_weight):
    open_list = PriorityQueue()
    open_list.put((0, start))
    
    came_from = {}
    g_score = {node: float('inf') for node in graph}
    g_score[start] = 0
    
    while not open_list.empty():
        _, current = open_list.get()
        
        if current == goal:
            break  # Path found
        
        for neighbor in graph[current]:
            tentative_g_score = g_score[current] + calculate_cost(current, neighbor, weather_data[neighbor], depth_data[neighbor], ship_weight)
            
            if tentative_g_score < g_score[neighbor]:
                g_score[neighbor] = tentative_g_score
                came_from[neighbor] = current
                open_list.put((tentative_g_score, neighbor))
    
  