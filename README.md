# SnapSort_Flask_Py_Anoth
A Flask-based app built in Python for analyzing images with GPS metadata. Features include location mapping, sorting by coordinates, and stats like most used camera models and frequently captured locations. Created as part of a software engineering project.


This is a Python Flask-based web application developed as part of my software engineering coursework. The app analyzes images containing GPS metadata and provides various insights, including mapping captured locations, keyword filtering from image text, and statistical analysis such as most used camera models and most captured locations.

📦 Python Packages Used
os, io: Handle file system operations and input/output streams.

folium: Used to generate interactive maps with GPS data.

exifread: Extracts EXIF metadata (including GPS coordinates and camera model) from images.

matplotlib.pyplot: Creates graphs and plots for statistical analysis.

csv: Reads and writes user registration and data files.

Flask: Lightweight web framework used to build this application.

werkzeug.utils: Helps with secure file uploading and password hashing.

opencage.geocoder: Converts GPS coordinates to human-readable location names using the OpenCage Geocoding API.

json: Handles reading and writing JSON data.

pytesseract: Optical Character Recognition (OCR) for extracting text from images.

PIL (Pillow): Opens and processes images.

cv2 (OpenCV): Used for image processing tasks.

re: Regular expressions for filtering and extracting text patterns.

werkzeug.security: Provides secure password hashing and verification.

📁 File Structure
users.csv: Stores new user registration data securely.

uploads/: Directory where user-uploaded images are stored.

🚀 How to Run
Click the Play button (or run the app locally with python app.py).

⚠️ Attention : Ensure that Miniconda is installed as the Python interpreter and run the application within that environment

Register or log in as a user.

Upload images with:

GPS Metadata: To map locations where the images were taken.

Text Captured: To perform keyword-based filtering using OCR.

View results:

Images displayed with location pins on a map.

Statistical graphs (e.g., most used camera models).

Keyword-matched images and location-based analytics.

📊 Features
Interactive maps of captured image locations.

Keyword search from image text using OCR.

Statistical analysis: most used camera models, most captured locations.

Secure user authentication and session handling.
