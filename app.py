import os
import io
import folium
import exifread
import matplotlib.pyplot as plt
import csv
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session
from werkzeug.utils import secure_filename
from opencage.geocoder import OpenCageGeocode
import json
import pytesseract
from PIL import Image
import cv2
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.urandom(24)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
UPLOAD_DIR = 'uploads'
USERS_CSV_FILE = 'users.csv'


for folder in ['uploads', 'static']:
    if not os.path.exists(folder):
        os.makedirs(folder)

OPENCAGE_API_KEY = 'b50de9c2f9a94fe884a3b9f18419781f'
geocoder = OpenCageGeocode(OPENCAGE_API_KEY)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(filepath):
    image = cv2.imread(filepath)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    temp_filename = 'temp_image.png'
    cv2.imwrite(temp_filename, binary_image)
    return temp_filename

def extract_text_from_image(filepath):
    preprocessed_image = preprocess_image(filepath)
    text = pytesseract.image_to_string(preprocessed_image)
    return text

def extract_metadata(filepath):
    with open(filepath, 'rb') as f:
        tags = exifread.process_file(f)
    
    metadata = {
        'date_time': str(tags.get('EXIF DateTimeOriginal', 'N/A')),
        'camera_model': str(tags.get('Image Model', 'N/A')),
        'gps_latitude': str(tags.get('GPS GPSLatitude', 'N/A')),
        'gps_longitude': str(tags.get('GPS GPSLongitude', 'N/A')),
        'ocr_text': extract_text_from_image(filepath)
    }

    if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
        lat = tags['GPS GPSLatitude'].values
        lon = tags['GPS GPSLongitude'].values
        lat_ref = tags['GPS GPSLatitudeRef'].values
        lon_ref = tags['GPS GPSLongitudeRef'].values
        latitude = (float(lat[0]) + float(lat[1])/60 + float(lat[2])/3600) * (-1 if lat_ref == 'S' else 1)
        longitude = (float(lon[0]) + float(lon[1])/60 + float(lon[2])/3600) * (-1 if lon_ref == 'W' else 1)
        result = geocoder.reverse_geocode(latitude, longitude)
        metadata['location'] = result[0]['formatted'] if result else 'N/A'
        metadata['latitude'] = latitude
        metadata['longitude'] = longitude
    else:
        metadata['location'] = 'N/A'
        metadata['latitude'] = None
        metadata['longitude'] = None

    return metadata

def validate_password(password):
    """Validate the password with required criteria"""
    return (len(password) >= 8 and
            re.search(r'[A-Z]', password) and
            re.search(r'[a-z]', password) and
            re.search(r'[0-9]', password) and
            re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

def validate_email(email):
    """Validate email format"""
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email)

def read_users_from_csv():
    """Read users from the CSV file"""
    users = {}
    if os.path.exists(USERS_CSV_FILE):
        with open(USERS_CSV_FILE, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 2:
                    username, hashed_password = row
                    users[username] = hashed_password
    return users

def write_user_to_csv(username, hashed_password):
    """Write a new user to the CSV file"""
    with open(USERS_CSV_FILE, mode='a') as file:
        writer = csv.writer(file)
        writer.writerow([username, hashed_password])

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('welcome'))
    return redirect(url_for('login'))

@app.route('/welcome')
def welcome():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')

        if not validate_email(username):
            return render_template('register.html', error="Username must be a valid email address.")
        
        if not validate_password(password):
            return render_template('register.html', error="Password must be at least 8 characters long and include 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special character.")
        
        if password != password_confirm:
            return render_template('register.html', error="Passwords do not match.")
        
        users = read_users_from_csv()
        if username in users:
            return render_template('register.html', error="User already exists.")
        
        hashed_password = generate_password_hash(password)
        write_user_to_csv(username, hashed_password)
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        users = read_users_from_csv()
        user_password = users.get(username)
        if user_password and check_password_hash(user_password, password):
            session['username'] = username
            return redirect(url_for('welcome'))
        else:
            return render_template('login.html', error="Invalid username or password.")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/upload_files', methods=['POST'])
def upload_files():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    files = request.files.getlist('files[]')
    metadata_list = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            metadata = extract_metadata(filepath)
            metadata['filename'] = filename
            metadata_list.append(metadata)
    
    return render_template('result.html', metadata_list=metadata_list)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/timeline')
def timeline():
    if 'username' not in session:
        return redirect(url_for('login'))

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    metadata_list = []
    for filename in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        metadata = extract_metadata(filepath)
        metadata['filename'] = filename
        if metadata['date_time'] != 'N/A':
            metadata_list.append(metadata)
    
    metadata_list.sort(key=lambda x: x['date_time'])
    
    return render_template('timeline.html', metadata_list=metadata_list)

@app.route('/map')
def map_view():
    if 'username' not in session:
        return redirect(url_for('login'))

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    folium_map = folium.Map(location=[0, 0], zoom_start=2)

    for filename in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.isfile(filepath):
            continue
        metadata = extract_metadata(filepath)
        metadata['filename'] = filename
        if metadata['latitude'] is not None and metadata['longitude'] is not None:
            folium.Marker(
                location=[metadata['latitude'], metadata['longitude']],
                icon=folium.CustomIcon(icon_image=filepath, icon_size=(50, 50)),
                popup=folium.Popup(f'<img src="{url_for("uploaded_file", filename=metadata["filename"])}" width="100"><br><strong>{metadata["location"]}</strong>', max_width=200)
            ).add_to(folium_map)

    map_html = folium_map._repr_html_()
    return render_template('map.html', map_html=map_html)

@app.route('/statistics')
def statistics():
    if 'username' not in session:
        return redirect(url_for('login'))

    files = os.listdir(app.config['UPLOAD_FOLDER'])
    locations = {}
    camera_models = {}

    for filename in files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        metadata = extract_metadata(filepath)
    
        if metadata['location'] != 'N/A':
            locations[metadata['location']] = locations.get(metadata['location'], 0) + 1
    
        if metadata['camera_model'] != 'N/A':
            camera_models[metadata['camera_model']] = camera_models.get(metadata['camera_model'], 0) + 1

    most_photographed_location = max(locations, key=locations.get, default='No valid locations found')
    most_used_camera_model = max(camera_models, key=camera_models.get, default='Unknown')

    location_data = {
        'labels': list(locations.keys()),
        'datasets': [{
            'label': 'Number of Photos',
            'data': list(locations.values()),
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'borderColor': 'rgba(75, 192, 192, 1)',
            'borderWidth': 1
        }]
    }

    camera_data = {
        'labels': list(camera_models.keys()),
        'datasets': [{
            'label': 'Number of Photos',
            'data': list(camera_models.values()),
            'backgroundColor': 'rgba(153, 102, 255, 0.2)',
            'borderColor': 'rgba(153, 102, 255, 1)',
            'borderWidth': 1
        }]
    }

    def safe_json_serialize(data):
        try:
            return json.dumps(data)
        except TypeError as e:
            print(f"Serialization error: {e}")
            return json.dumps({})

    return render_template('statistics.html',
                        most_photographed_location=most_photographed_location,
                        most_used_camera_model=most_used_camera_model,
                        location_data=location_data,
                        camera_data=camera_data)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        keyword = request.form.get('keyword', '').lower()
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        search_results = []

        for filename in files:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            metadata = extract_metadata(filepath)
            metadata['filename'] = filename
            if keyword in metadata.get('ocr_text', '').lower():
                search_results.append(metadata)
                
        session['search_results'] = search_results
        session['keyword'] = keyword

        return redirect(url_for('search_result'))
    return render_template('search.html')

@app.route('/search_result')
def search_result():
    if 'username' not in session:
        return redirect(url_for('login'))

    search_results = session.get('search_results', [])
    keyword = session.get('keyword', '')

    return render_template('search_result.html', search_results=search_results, keyword=keyword)

if __name__ == '__main__':
    app.run(debug=True)
