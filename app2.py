
import requests
from flask import Flask, Response, render_template, request, redirect, render_template_string, url_for
import os
import csv
import ast
import time
import threading

# --- BARCODE DECODING IMPORTS ---
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

# --- Global State for Continuous Scanning (Shared) ---
lock = threading.Lock()
scanning = False
last_decoded_data = None
scan_thread = None

# --- Configuration for Scanner ---
# !! UPDATE THIS IP TO MATCH YOUR ESP32-CAM !!
ESP32_CAM_IP = "192.168.1.132"
IMAGE_URL = f"http://{ESP32_CAM_IP}/"
OUTPUT_FILENAME = "last_captured_barcode.jpg"


def create_app(config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')

    # -----------------------------------------------------
    # App config
    # -----------------------------------------------------
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key'),
        CSV_FILE=os.path.join(app.root_path, 'database/products.csv')
    )

    if config:
        app.config.update(config)

    # -----------------------------------------------------
    # HELPER FUNCTIONS: SEARCH AND ALLERGY CHECK (UPDATED)
    # -----------------------------------------------------

    def search_product_by_name(product_name, csv_file):
        """Searches CSV for a product name and returns its location coords and allergen list."""
        try:
            with open(csv_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name", "").lower() == product_name.lower():
                        # Safely convert coordinate strings to Python objects (tuples)
                        coords = (ast.literal_eval(row["X"]), ast.literal_eval(row["Y"]), ast.literal_eval(row["Z"]))
                        allergens_raw = row.get("Allergens", "None")
                        product_name_found = row["Name"]
                        return coords, allergens_raw, product_name_found
            return None, None, None
        except FileNotFoundError:
            print(f"ERROR: CSV file not found at {csv_file}")
            return None, None, None
        except Exception as e:
            print(f"ERROR during name search: {e}")
            return None, None, None

    def search_product_by_barcode(barcode_data, csv_file):
        """Searches CSV for a barcode string and returns its location coords and allergen list."""
        try:
            with open(csv_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Barcode") == barcode_data:
                        coords = (ast.literal_eval(row["X"]), ast.literal_eval(row["Y"]), ast.literal_eval(row["Z"]))
                        allergens_raw = row.get("Allergens", "None")
                        product_name_found = row["Name"]
                        return coords, allergens_raw, product_name_found

            return None, None, None
        except FileNotFoundError:
            print(f"ERROR: CSV file not found at {csv_file}")
            return None, None, None
        except Exception as e:
            print(f"ERROR during barcode search: {e}")
            return None, None, None

    def check_safety(user_allergy, product_allergens):
        """Compares the user's allergy to the product's allergens."""
        # If user has no allergy selected, it's always safe to track.
        if user_allergy == "None":
            return True, "Product found! Please follow Pepper Robot."

        # Split and clean the product's allergen list for comparison
        product_allergen_list = [a.strip().lower() for a in product_allergens.split(',')]
        user_allergy_lower = user_allergy.lower()

        # Check if the user's allergy is in the product's allergen list
        if user_allergy_lower in product_allergen_list:
            return False, f"🛑 UNSAFE: Contains **{user_allergy}**."

        # Safe to track
        return True, "Product found! Please follow Pepper Robot."

    # -----------------------------------------------------
    # HELPER FUNCTIONS: BARCODE SCANNING THREAD LOGIC
    # -----------------------------------------------------

    def decode_saved_image(image_path):
        """Decodes barcodes and QR codes from the locally saved image file."""
        global last_decoded_data

        if not os.path.exists(image_path):
            return False

        try:
            img = Image.open(image_path)
            decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE, ZBarSymbol.EAN13, ZBarSymbol.CODE128])

            if decoded_objects:
                data = decoded_objects[0].data.decode('utf-8')
                code_type = decoded_objects[0].type
                print(f"--- DECODED {code_type}: {data} ---")

                with lock:
                    global scanning
                    scanning = False  # Stop the loop after a successful read
                    last_decoded_data = data
                return True

            return False

        except Exception as e:
            print(f"FATAL DECODE ERROR: {e}")
            return False

    def continuous_scan_loop():
        """Runs in a separate thread. Captures, saves, and decodes images until 'scanning' is False."""
        global scanning
        print("\n--- Starting Continuous Barcode Scanning Thread ---")
        SCAN_DELAY_SECONDS = 0.5

        while True:
            with lock:
                if not scanning:
                    print("--- Scanning thread received stop signal. Exiting. ---")
                    break

            # 1. Fetch Image from ESP32-CAM
            try:
                response = requests.get(IMAGE_URL, timeout=5)
                response.raise_for_status()
                image_bytes = response.content
            except requests.exceptions.RequestException as e:
                print(f"ERROR: Could not fetch image from ESP32: {e}")
                time.sleep(SCAN_DELAY_SECONDS * 2)
                continue

            # 2. Save Image Locally
            try:
                with open(OUTPUT_FILENAME, 'wb') as f:
                    f.write(image_bytes)
            except Exception as e:
                print(f"ERROR: Could not save file {OUTPUT_FILENAME}: {e}")

            # 3. ATTEMPT BARCODE DECODING
            decode_saved_image(OUTPUT_FILENAME)

            # 4. Wait for the next scan attempt
            time.sleep(SCAN_DELAY_SECONDS)

    # -----------------------------------------------------
    # FLASK ROUTES
    # -----------------------------------------------------    
    @app.route('/')
    def index():
        """Serves the initial user input page (index.html)."""
        return render_template('index.html')

    @app.route('/product', methods=['GET', 'POST'])
    def product_page():
        """Handles user entry, manual search, and result display with allergy check (UPDATED)."""

        user_name = request.values.get("name", "there")
        allergy = request.values.get("allergy", "")

        result = request.args.get("result", None)
        coords = None  # Coordinates are no longer displayed on the page

        if request.method == 'POST':
            product_name = request.form.get("product")

            # Search returns (coords, allergens)
            coords_tuple, allergens = search_product_by_name(product_name, app.config['CSV_FILE'])

            if coords_tuple:
                is_safe, safety_message = check_safety(allergy, allergens)

                if is_safe:
                    # Safe product found. Display success message
                    result = f"✅ {safety_message}"
                else:
                    # Dangerous product found. Display warning and stop
                    result = f"{safety_message} DO NOT CONSUME."
            else:
                result = f"Sorry, '{product_name}' was not found in the database."

        return render_template(
            'product.html',
            name=user_name,
            allergy=allergy,
            result=result,
            coords=coords
        )

    # -----------------------------------------------------
    # ROUTE: START SCANNING
    # -----------------------------------------------------    
    @app.route('/scan', methods=['POST'])
    def scan_start_trigger():
        """Starts the scanning thread and redirects to the status page."""
        global scanning, scan_thread, last_decoded_data

        user_name = request.form.get("name", "there")
        allergy = request.form.get("allergy", "")

        with lock:
            last_decoded_data = None

            if scan_thread is None or not scan_thread.is_alive():
                scanning = True

                new_scan_thread = threading.Thread(target=continuous_scan_loop, daemon=True)
                new_scan_thread.start()
                scan_thread = new_scan_thread
            else:
                scanning = True

        return redirect(f'/scanner_status?name={user_name}&allergy={allergy}')

    # -----------------------------------------------------
    # ROUTE: SCANNER STATUS (HTML PRESERVED AS REQUESTED)
    # -----------------------------------------------------    
    @app.route('/scanner_status', methods=['GET'])
    def scanner_status():
        """Page that waits and checks the global state for a decoded barcode."""
        global last_decoded_data

        with lock:
            current_barcode = last_decoded_data

        user_name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")

        if current_barcode:
            # BARCODE FOUND: TRIGGER CSV LOOKUP and REDIRECT 

            # If product is not found, this returns (None, None, None)
            coords_tuple, allergens, name_found = search_product_by_barcode(current_barcode, app.config['CSV_FILE'])

            if coords_tuple:
                # --- PRODUCT FOUND IN DATABASE ---
                is_safe, safety_message = check_safety(allergy, allergens)

                if is_safe:
                    # Safe product found. Use product name in message.
                    result_msg = (
                        f"✅ **{name_found}** decoded! This product is good to eat. Please follow Pepper Robot."
                    )
                else:
                    # Dangerous product found. Use product name in message.
                    result_msg = (
                        f"⚠️ **{name_found}** decoded. {safety_message} **DO NOT EAT.**"
                    )

                coords_str = None
            else:
                # --- PRODUCT NOT FOUND (coords_tuple is None) ---
                # Must use current_barcode in the warning message, not name_found
                result_msg = f"⚠️ Barcode **{current_barcode}** decoded, but product not found in database."
                coords_str = None

            # Global state reset and redirect MUST happen after the checks
            with lock:
                last_decoded_data = None

                    # Redirect to product_page with the new safety message
            return redirect(
                url_for('product_page', name=user_name, allergy=allergy, result=result_msg, coords=coords_str)
            )
        return render_template_string("""
                               <!DOCTYPE html>
                                <html lang="en">
                                <head>
                                    <meta charset="UTF-8">
                                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                    <title>Scanning...</title>
                                    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
                                    <meta http-equiv="refresh" content="2">
                                </head>
                                <body
                                style="
                                    background: linear-gradient(135deg, #dbe8e8, #f2f8f8); 
                                ">
            

                                    <div class="container">
                                        <h1 style="color: #197278;">Scanning Barcode...</h1>

                                        <p style="margin-bottom: 20px; color: #333;">
                                            Scanning camera (IP: {}). Please hold the product steady.
                                        </p>

                                        <img src="/latest_image" alt="Live Scanner Feed"/>

                                        <p style="font-size: 0.9em; margin-top: 20px; color: #777;">
                                            This page refreshes automatically.
                                        </p>
                                    </div>
                                </body>
                                </html>
                            """.format(ESP32_CAM_IP))

        # -----------------------------------------------------
        # ROUTE: IMAGE SERVICE
        # -----------------------------------------------------

    @app.route('/latest_image')
    def latest_image():
        """Serves the most recently saved image file from the background scanner."""
        try:
            with open(OUTPUT_FILENAME, 'rb') as f:
                image_bytes = f.read()
            return Response(image_bytes, mimetype='image/jpeg')
        except FileNotFoundError:
            return Response("Waiting for camera connection...", status=404)
        except Exception as e:
            return Response(f"Error serving image: {e}", status=500)

    return app


# -----------------------------------------------------
# EXECUTION BLOCK
# -----------------------------------------------------
if __name__ == '__main__':
    app = create_app()
    # use_reloader=False is set when using threading
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
