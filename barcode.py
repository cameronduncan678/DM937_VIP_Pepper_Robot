import requests
from flask import Flask, Response, render_template_string
import os
import time
import threading

# --- NEW IMPORTS FOR BARCODE DECODING ---
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

# ----------------------------------------

# --- Configuration ---
#Update this IP - this should be changed depending on wifi IP 
ESP32_CAM_IP = "10.233.119.250"
#stream/snapshot URL for the ESP32-CAM
IMAGE_URL = f"http://{ESP32_CAM_IP}/"

# --- File Save Configuration ---
OUTPUT_FILENAME = "last_captured_barcode.jpg"

# --- Global State for Scanning ---
# Use a lock to safely control access to shared variables like the 'scanning' flag
lock = threading.Lock()
# Flag to control the scanning loop
scanning = True
# Store the result so the web page can display it
last_decoded_data = "Scanning..."

app = Flask(__name__)


# --- Barcode Decoding Function (Remains the same) ---

def decode_saved_image(image_path):
    """
    Decodes barcodes and QR codes from the locally saved image file.
    """
    global last_decoded_data
    if not os.path.exists(image_path):
        print(f"DECODE ERROR: Image file not found at {image_path}")
        return False

    try:
        img = Image.open(image_path)
        decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE, ZBarSymbol.EAN13, ZBarSymbol.CODE128])

        if decoded_objects:
            # Found a barcode!
            print("\n--- BARCODE DECODED SUCCESSFULLY ---")
            decoded_info = []
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                code_type = obj.type
                print(f"DECODED TYPE: {code_type}")
                print(f"DECODED DATA: {data}")
                decoded_info.append(f"{code_type}: {data}")
            print("------------------------------------\n")

            with lock:
                # Update global state and stop scanning
                global scanning
                scanning = False
                last_decoded_data = "<br>".join(decoded_info)
            return True  # Barcode found

        else:
            print("DECODE RESULT: No barcode or QR code found in the image. Continuing scan.")
            return False  # No barcode found

    except Exception as e:
        print(f"FATAL DECODE ERROR: Could not process image. REASON: {e}")
        return False


# --- Continuous Scanning Loop (NEW) ---

def continuous_scan_loop():
    """
    Runs in a separate thread. Continuously captures, saves, and decodes images.
    """
    global scanning
    print("\n--- Starting Continuous Barcode Scanning Thread ---")

    # Set a rate limit (e.g., capture one image per second)
    SCAN_DELAY_SECONDS = 1.0

    while True:
        with lock:
            if not scanning:
                print("--- Scanning stopped due to successful decode or manual stop. ---")
                break  # Exit the loop if scanning is set to False

        print("-" * 30)
        print(f"1. Attempting to fetch image from: {IMAGE_URL}")

        # 1. Fetch Image from ESP32-CAM
        try:
            # Set a shorter timeout for quicker loop iterations
            response = requests.get(IMAGE_URL, timeout=5)
            response.raise_for_status()
            image_bytes = response.content
            print(f"2. Image fetched successfully. Size: {len(image_bytes)} bytes.")

        except requests.exceptions.RequestException as e:
            error_msg = f"ERROR: Could not fetch image from ESP32: {e}"
            print(error_msg)
            # Wait before trying again
            time.sleep(SCAN_DELAY_SECONDS)
            continue  # Go to the next loop iteration

        # 2. Save Image Locally
        try:
            with open(OUTPUT_FILENAME, 'wb') as f:
                f.write(image_bytes)
            print(f"3. Image saved successfully as: {OUTPUT_FILENAME}")
        except Exception as e:
            print(f"ERROR: Could not save file {OUTPUT_FILENAME}: {e}")

        # 3. ATTEMPT BARCODE DECODING
        # decode_saved_image will handle updating the global 'scanning' flag if successful.
        decode_saved_image(OUTPUT_FILENAME)

        # 4. Wait for the next scan attempt
        time.sleep(SCAN_DELAY_SECONDS)


# --- Flask Routes ---

# We can remove /image_snapshot as the background thread now handles the capture/decode

@app.route('/')
def index():
    """
    Renders the HTML page to display the last captured image and the decoding status.
    """
    # NOTE: The image displayed here is the *last saved* image from the background thread.
    return render_template_string(f"""
    <html>
        <head>
            <title>ESP32-CAM Barcode Scanner</title>
            <style>
                body {{ font-family: sans-serif; text-align: center; }}
                img {{ max-width: 90%; border: 1px solid #ccc; margin-top: 20px; }}
            </style>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="3"> </head>
        <body>
            <h1>ESP32-CAM Barcode Scanner</h1>
            <p>The system is **automatically** scanning in the background.</p>

            <h2>Scanning Status:</h2>
            <div style="font-size: 1.5em; color: {'green' if 'DECODED' in last_decoded_data else 'red'}; font-weight: bold;">
                {last_decoded_data}
            </div>

            <p>Last Image Captured:</p>
            <img src="/latest_image">
            <p style="margin-top: 30px; color: #555;">The console shows detailed scan progress.</p>
        </body>
    </html>
    """)


@app.route('/latest_image')
def latest_image():
    """
    Serves the most recently saved image file.
    """
    try:
        with open(OUTPUT_FILENAME, 'rb') as f:
            image_bytes = f.read()
        return Response(image_bytes, mimetype='image/jpeg')
    except FileNotFoundError:
        return Response("Waiting for first image capture...", status=404)
    except Exception as e:
        return Response(f"Error serving image: {e}", status=500)


# --- Execution ---

if __name__ == '__main__':
    # 1. Start the continuous scanning loop in a separate thread
    scan_thread = threading.Thread(target=continuous_scan_loop)
    # Set as daemon so the thread doesn't prevent the main program from exiting
    scan_thread.daemon = True
    scan_thread.start()

    # 2. Run the Flask web server
    print("--- Starting Flask Web Server on http://0.0.0.0:5000 ---")
    app.run(host='0.0.0.0', port=5000)
