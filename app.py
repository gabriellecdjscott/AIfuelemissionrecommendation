from flask import Flask, request, jsonify, render_template
import requests
import os

app = Flask(__name__)
checkwx_api_key = os.getenv('CHECKWX_API_KEY', 'a741a79a6d7246f8a3e0364dc8')

# Function to fetch weather data from CheckWX API
def get_weather(api_key, icao_code):
    url = f'https://api.checkwx.com/metar/{icao_code}/decoded'
    headers = {'X-API-Key': api_key}
    response = requests.get(url, headers=headers)
    return response.json()

# Helper functions
def extract_wind_speed(weather_data):
    try:
        return weather_data['data'][0]['wind']['speed_kts']
    except (IndexError, KeyError):
        return None

def extract_temperature(weather_data):
    try:
        return weather_data['data'][0]['temperature']['value']
    except (IndexError, KeyError):
        return None

def check_weather_conditions(weather_data):
    try:
        weather_conditions = weather_data['data'][0]['weather']
        is_rainfall = any(condition['value'] in ['RA', 'TSRA'] for condition in weather_conditions)
        is_thunderstorms = any(condition['value'] == 'TS' for condition in weather_conditions)
        return is_rainfall, is_thunderstorms
    except (IndexError, KeyError):
        return False, False

def calculate_emissions(flight_distance, wind_speed):
    baseline_emissions = flight_distance * 0.1
    if wind_speed is not None and wind_speed > 10:
        adjusted_emissions = baseline_emissions * 0.9
    else:
        adjusted_emissions = baseline_emissions
    return adjusted_emissions

def generate_recommendations(emissions):
    if emissions < 100:
        return "Your flight emissions are relatively low. Consider offsetting them with a carbon offset program."
    elif emissions >= 100 and emissions < 200:
        return "Your flight emissions are moderate. You may want to choose a more fuel-efficient airline for future flights."
    else:
        return "Your flight emissions are high. Consider alternative transportation options or carbon offset programs."

@app.route('/')
def index():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        icao_code = data.get('icao_code', '').strip()
        flight_distance_str = data.get('flight_distance', '0').strip()

        if not icao_code:
            return jsonify({'error': 'Missing ICAO code'}), 400
        try:
            flight_distance = float(flight_distance_str)
        except ValueError:
            return jsonify({'error': 'Invalid flight distance format'}), 400

        # Fetch weather data
        weather_data = get_weather(checkwx_api_key, icao_code)
        wind_speed = extract_wind_speed(weather_data)
        temperature = extract_temperature(weather_data)
        is_rainfall, is_thunderstorms = check_weather_conditions(weather_data)

        # Calculate emissions
        emissions = calculate_emissions(flight_distance, wind_speed)
        recommendations = generate_recommendations(emissions)

        # Compose response message
        weather_info = []
        if temperature is not None:
            weather_info.append(f"Temperature: {temperature} °C")
        if wind_speed is not None:
            weather_info.append(f"Wind Speed: {wind_speed} kt")
        weather_info.append(f"Rainfall: {'Yes' if is_rainfall else 'No'}")
        weather_info.append(f"Thunderstorms: {'Yes' if is_thunderstorms else 'No'}")

        message = f"Current Weather Conditions:\n" + '\n'.join(weather_info) + \
                  f"\n\nEmissions: {emissions:.2f} kg CO2. {recommendations}"

        return jsonify({'message': message})
    except Exception as e:
        return jsonify({'error': f"Error processing request: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
