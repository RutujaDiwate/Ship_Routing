from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import heapq
from collections import defaultdict
import logging
import math

app = Flask(_name_)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(_name_)

# Load the data

def load_data():
    try:
        with open('global_ports_locations.geojson') as f:
            ports_data = json.load(f)
        logger.info(f"Loaded {len(ports_data['features'])} ports")
        
        with open('major_routes.json') as f:
            routes_data = json.load(f)
        logger.info(f"Loaded {len(routes_data['routes'])} routes")
        
        return ports_data, routes_data
    except FileNotFoundError as e:
        logger.error(f"Failed to load data files: {e}")
        raise

# Create a graph representation of the routes
def create_graph(routes_data):
    graph = defaultdict(list)
    route_details = {}
    
    for route in routes_data['routes']:
        from_port = route['from']
        to_port = route['to']
        distance = route['distance']
        route_path = [{'latitude': point['latitude'], 'Longtitude': point['Longtitude']} for point in route['route']]
        
        graph[from_port].append((to_port, distance))
        graph[to_port].append((from_port, distance))
        
        route_details[(from_port, to_port)] = route_path
        route_details[(to_port, from_port)] = route_path[::-1]
    
    logger.info(f"Created graph with nodes: {dict(graph)}")  # Added for debugging
    return graph, route_details

# Modified Dijkstra's algorithm with fuel constraint
def find_route(graph, start, end, max_fuel, ports_data, route_details, storms):
    logger.info(f"Finding route from port {start} to {end} with max fuel {max_fuel}")

    if start not in graph:
        logger.warning(f"Start port {start} not found in graph")
        return None
    if end not in graph:
        logger.warning(f"End port {end} not found in graph")
        return None

    pq = [(0, start, [start], [])]
    visited = set()

    while pq:
        total_distance, current, path, coords = heapq.heappop(pq)
        logger.debug(f"Visiting port {current}, total distance so far: {total_distance}")

        if current == end:
            logger.info(f"Found route! Total distance: {total_distance}")
            port_details = []
            for port_id in path:
                port_feature = next(
                    (f for f in ports_data['features'] if f['properties']['id'] == port_id),
                    None
                )
                if port_feature:
                    port_details.append({
                        'id': port_id,
                        'name': port_feature['properties']['name'],
                        'coordinates': port_feature['geometry']['coordinates']
                    })

            return {
                'success': True,
                'total_distance': total_distance,
                'path': path,
                'ports': port_details,
                'route_coordinates': coords
            }

        if current in visited:
            continue

        visited.add(current)

        for next_port, segment_distance in graph[current]:
            if segment_distance <= max_fuel:
                logger.debug(f"Considering route {current} -> {next_port} (distance: {segment_distance})")

                route_key = (current, next_port)
                segment_coords = route_details.get(route_key, [])

                # Check if the path goes through a storm area
                if is_path_in_storm(segment_coords, storms):
                    logger.debug(f"Route {current} -> {next_port} is within a storm zone. Skipping.")
                    continue

                new_distance = total_distance + segment_distance
                new_path = path + [next_port]
                new_coords = coords + segment_coords

                heapq.heappush(pq, (new_distance, next_port, new_path, new_coords))
            else:
                logger.debug(
                    f"Skipping route {current} -> {next_port} (distance {segment_distance} exceeds fuel capacity)")

    logger.warning("No valid route found")
    return None



def haversine(coord1, coord2):
    """
    Calculate the Haversine distance between two points in kilometers.
    """
    R = 6371  # Radius of the Earth in kilometers
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def is_path_in_storm(path_coords, storms):
    """
    Check if any point in the path intersects with a storm radius.
    """
    for point in path_coords:
        point_coords = (point['latitude'], point['Longtitude'])
        for storm in storms:
            storm_center = (storm['coordinates'][1], storm['coordinates'][0])  # Reverse to match (lat, lon)
            storm_radius = float(storm['radius'])
            distance = haversine(point_coords, storm_center)
            if distance <= storm_radius:
                logger.debug(f"Point {point_coords} is within storm radius of {storm_center} (radius: {storm_radius} km)")
                return True  # Path intersects with a storm zone
    return False

@app.route('/api/route', methods=['POST'])
def get_route():
    data = request.get_json()
    logger.info(f"Received request with data: {data}")

    try:
        start_port = int(data.get('start'))
        end_port = int(data.get('end'))
        max_fuel = int(data.get('maxFuel'))
        print(start_port, end_port, max_fuel)

        # Load data and create graph
        with open('global_ports_locations.geojson') as f:
            ports_data = json.load(f)
        with open('major_routes.json') as f:
            routes_data = json.load(f)
        with open('storm.json') as f:
            storms = json.load(f)['locations']

        graph, route_details = create_graph(routes_data)

        # Find route
        result = find_route(graph, start_port, end_port, max_fuel, ports_data, route_details, storms)

        if result:
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'message': 'No valid route found with the given fuel constraint storm avoidance'
            })
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if _name_ == '_main_':
    app.run(debug=True)