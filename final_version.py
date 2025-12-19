import requests
from flask import Flask, Response, render_template, request, redirect, render_template_string, url_for
import os
import csv
import ast
import time
import threading
import subprocess

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
ESP32_CAM_IP = "10.233.119.250"
IMAGE_URL = f"http://{ESP32_CAM_IP}/"
OUTPUT_FILENAME = "last_captured_barcode.jpg"
# --- External Script Paths ---
PEPPER_SCRIPT_NAME_1 = r"C:\Users\roisi\Downloads\testing.py"
PEPPER_SCRIPT_NAME_2 = r"C:\Users\roisi\Downloads\move_head.py"


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
    # HELPER FUNCTIONS: PEPPER EXECUTION (SEQUENTIAL & ASYNCHRONOUS)
    # -----------------------------------------------------

    def run_external_script(script_path, name="Script"):
        """Executes an external Python 2.7 script synchronously (blocking)."""
        python27_executable = "py"
        command = [
            python27_executable,
            "-2.7",
            script_path
        ]

        try:
            print(f"\n--- LAUNCHING {name}: {script_path} ---")

            # Use run() for simple execution and waiting, discarding output
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,  # Don't raise exception on non-zero exit code
                close_fds=True
            )

            print(f"{name} finished with return code {result.returncode}.")
            return result.returncode == 0

        except Exception as e:
            print(f"FATAL LAUNCH FAILURE for {name}: {e}")
            return False

    def run_pepper_sequence(coords_tuple=None):
        """
        Runs sequentially in a dedicated background thread:
        1. Runs testing.py.
        2. If testing.py succeeds, runs move_head.py.
        """

        # --- SCRIPT 1: testing.py ---
        script1_success = run_external_script(PEPPER_SCRIPT_NAME_1, name="testing.py")

        if script1_success:
            print("testing.py completed successfully. Proceeding to move_head.py.")
            # We can optionally sleep here if there needs to be a gap between robot movements
            # time.sleep(1)

            # --- SCRIPT 2: move_head.py ---
            script2_success = run_external_script(PEPPER_SCRIPT_NAME_2, name="move_head.py")

            if script2_success:
                print("move_head.py completed successfully. Sequence finished.")
            else:
                print("WARNING: move_head.py failed or returned an error.")
        else:
            print("FATAL: testing.py failed. Aborting sequence.")

        return script1_success  # We'll consider the sequence successful if the first script launched (even if the second failed)

    def execute_pepper_motion(coords_tuple=None):
        """
        Executes the Pepper script sequence ASYNCHRONOUSLY by starting a new thread.
        It returns immediately after launching the thread.
        Returns: (launch_success: bool, message: str)
        """
        try:
            # Launch the entire two-script sequence in a new daemon thread
            sequence_thread = threading.Thread(
                target=run_pepper_sequence,
                args=(coords_tuple,),
                daemon=True
            )
            sequence_thread.start()

            print(f"Pepper sequence thread launched. Proceeding immediately.")
            return True, "Pepper motion sequence successfully initiated (testing.py -> move_head.py)."

        except Exception as e:
            error_details = f"FATAL THREAD LAUNCH FAILURE: {e}"
            print(error_details)
            return False, error_details

    # -----------------------------------------------------
    # HELPER FUNCTIONS: SEARCH AND ALLERGY CHECK (NO CHANGE)
    # -----------------------------------------------------

    def search_product_by_name(product_name, csv_file):
        """Searches CSV for a product name and returns its location coords and allergen list."""
        try:
            # Using Python 3 specific CSV handling
            with open(csv_file, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("Name", "").lower() == product_name.lower():
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
        if user_allergy == "None":
            return True, "Product found! Please follow Pepper Robot."

        product_allergen_list = [a.strip().lower() for a in product_allergens.split(',')]
        user_allergy_lower = user_allergy.lower()

        if user_allergy_lower in product_allergen_list:
            return False, f"🛑 UNSAFE: Contains **{user_allergy}**."

        return True, "Product found! Please follow Pepper Robot."

    # -----------------------------------------------------
    # HELPER FUNCTIONS: BARCODE SCANNING THREAD LOGIC (NO CHANGE)
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
        SCAN_DELAY_SECONDS = 0.2

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
    # FLASK ROUTES (NO CHANGE to logic flow)
    # -----------------------------------------------------
    @app.route('/')
    def index():
        """Serves the initial user input page (index.html)."""
        return render_template('index.html')

    @app.route('/product', methods=['GET', 'POST'])
    def product_page():
        """
        Handles user entry.
        On POST: Executes Pepper motion sequence (non-blocking), waits 20 seconds, then redirects to start scanning.
        """

        user_name = request.values.get("name", "there")
        allergy = request.values.get("allergy", "")
        result = request.args.get("result", None)

        if request.method == 'POST':
            product_name = request.form.get("product")

            # --- STAGE 1A: PEPPER ACTION (ASYNCHRONOUS LAUNCH) ---
            coords_tuple, _, _ = search_product_by_name(product_name, app.config['CSV_FILE'])

            # Run the Pepper script sequence and RETURN IMMEDIATELY.
            pepper_success, pepper_message = execute_pepper_motion(coords_tuple)

            action_result = ""
            if pepper_success:
                # Script thread launched successfully.
                action_result = f"✅ Pepper action sequence initiated. **Waiting 20 seconds for Pepper to move** before starting barcode scan for product: **{product_name}**."

                # --- STAGE 1B: ARTIFICIAL DELAY (BLOCKING) ---
                print("Starting 20-second artificial delay (concurrent with Pepper movement)...")
                time.sleep(20)  # *** 1- DELAY STARTS AFTER LAUNCH ***
                print("20-second delay finished. Redirecting to scanning.")
                action_result = f"✅ Now starting barcode scan for product: **{product_name}**."

            else:
                # Launch failure (failure to run the 'py -2.7' command itself)
                error_snippet = pepper_message[:150].split('\n')[0]
                action_result = (
                    f"⚠️ Pepper launch failed! Error: `{error_snippet}...`. "
                    f"Proceeding immediately to barcode scan for product: {product_name}."
                )

            # --- STAGE 2: REDIRECT TO START SCANNING ---
            return redirect(url_for(
                'start_scanning',
                name=user_name,
                allergy=allergy,
                product=product_name,
                action_status=action_result
            ))

        # For GET request (after successful scan or initial load)
        return render_template(
            'product.html',
            name=user_name,
            allergy=allergy,
            result=result,
            coords=None
        )

    # -----------------------------------------------------
    # ROUTE: START SCANNING
    # -----------------------------------------------------
    @app.route('/start_scanning', methods=['GET'])
    def start_scanning():
        """Starts the scanning thread and immediately redirects to the status page."""
        global scanning, scan_thread, last_decoded_data

        user_name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")
        product_name = request.args.get("product", "")
        action_status = request.args.get("action_status", "Scanning started.")

        with lock:
            last_decoded_data = None

            if scan_thread is None or not scan_thread.is_alive():
                scanning = True

                new_scan_thread = threading.Thread(target=continuous_scan_loop, daemon=True)
                new_scan_thread.start()
                scan_thread = new_scan_thread
            else:
                scanning = True

        return redirect(url_for(
            'scanner_status',
            name=user_name,
            allergy=allergy,
            product=product_name,
            action_status=action_status
        ))

    # -----------------------------------------------------
    # ROUTE: SCANNER STATUS (POLLING/CHECKING) - CACHE BUSTER ADDED
    # -----------------------------------------------------
    @app.route('/scanner_status', methods=['GET'])
    def scanner_status():
        """Page that waits and checks the global state for a decoded barcode."""
        global last_decoded_data

        with lock:
            current_barcode = last_decoded_data

        user_name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")
        product_name = request.args.get("product", "")
        action_status = request.args.get("action_status", "Scanning...")

        if current_barcode:
            # BARCODE FOUND: TRIGGER CSV LOOKUP and REDIRECT
            coords_tuple, allergens, name_found = search_product_by_barcode(current_barcode, app.config['CSV_FILE'])

            if coords_tuple:
                # --- PRODUCT FOUND IN DATABASE ---
                is_safe, safety_message = check_safety(allergy, allergens)

                if is_safe:
                    result_msg = (
                        f"✅ {name_found} decoded! Product is safe. Please follow Pepper Robot."
                    )
                else:
                    result_msg = (
                        f"⚠️ {name_found} decoded. {safety_message} DO NOT EAT."
                    )

            else:
                # --- PRODUCT NOT FOUND (coords_tuple is None) ---
                result_msg = f"⚠️ Barcode **{current_barcode}** decoded, but product not found in database."

            with lock:
                last_decoded_data = None

            return redirect(
                url_for('product_page', name=user_name, allergy=allergy, result=result_msg)
            )

        # Generate a unique timestamp to defeat browser caching
        cache_buster = int(time.time() * 1000)

        # No barcode found yet, keep polling and display the action status
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

                                        <div style="font-weight: bold; color: #197278; margin-bottom: 10px;">
                                            Action Status: {}
                                        </div>

                                        <img src="/latest_image?t={}" alt="Live Scanner Feed"/>

                                        <p style="font-size: 0.9em; margin-top: 20px; color: #777;">
                                            This page refreshes automatically.
                                        </p>
                                    </div>
                                </body>
                                </html>
                            """.format(ESP32_CAM_IP, action_status, cache_buster))

    # -----------------------------------------------------
    # ROUTE: IMAGE SERVICE
    # -----------------------------------------------------

    @app.route('/latest_image')
    def latest_image():
        """Serves the most recently saved image file from the background scanner."""
        try:
            with open(OUTPUT_FILENAME, 'rb') as f:
                image_bytes = f.read()
            # Adding cache control headers to encourage (but not force) re-request
            response = Response(image_bytes, mimetype='image/jpeg')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except FileNotFoundError:
            return Response("Waiting for camera connection...", status=404)
        except Exception as e:
            return Response(f"Error serving image: {e}", status=500)

    return app


# -----------------------------------------------------
# EXECUTION BLOCK
# -----------------------------------------------------
if __name__ == '__main__':
    # Ensure subprocess.DEVNULL is available for non-blocking processes
    try:
        from subprocess import DEVNULL
    except ImportError:
        DEVNULL = open(os.devnull, 'w')
        subprocess.DEVNULL = DEVNULL

    app = create_app()
    # use_reloader=False is necessary when using threading
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
