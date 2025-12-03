import requests
from flask import Flask, Response, render_template_string
import os
# --- NEW IMPORTS FOR BARCODE DECODING ---
from PIL import Image
from pyzbar.pyzbar import decode, ZBarSymbol

# ----------------------------------------

# --- Configuration ---
# !!! IMPORTANT: Update this IP
ESP32_CAM_IP = "10.233.119.250"
IMAGE_URL = f"http://10.233.119.250"

# --- File Save Configuration ---
OUTPUT_FILENAME = "last_captured_barcode.jpg"

app = Flask(__name__)


# --- Barcode Decoding Function ---

def decode_saved_image(image_path):
    """
    Decodes barcodes and QR codes from the locally saved image file.
    Output is printed to the server console (Command Prompt).
    """
    if not os.path.exists(image_path):
        print(f"DECODE ERROR: Image file not found at {image_path}")
        return

    try:
        # 1. Open the image using Pillow
        img = Image.open(image_path)

        # 2. Decode the image using ZBar
        # We search for QR Code, EAN-13, and Code 128
        decoded_objects = decode(img, symbols=[ZBarSymbol.QRCODE, ZBarSymbol.EAN13, ZBarSymbol.CODE128])

        if decoded_objects:
            print("\n--- BARCODE DECODED SUCCESSFULLY ---")
            for obj in decoded_objects:
                # Decode the data from bytes to a readable string
                data = obj.data.decode('utf-8')
                code_type = obj.type
                print(f"DECODED TYPE: {code_type}")
                print(f"DECODED DATA: {data}")
            print("------------------------------------\n")
            return decoded_objects
        else:
            print("DECODE RESULT: No barcode or QR code found in the image.")
            return []

    except Exception as e:
        # This common error is the ZBar system library not being found.
        print(f"\nFATAL DECODE ERROR: Could not process image.")
        print(f"REASON: {e}")
        print("ACTION: Ensure the ZBar Windows Installer (zbar-0.10-setup.exe) has been run!")
        print("-" * 30)
        return []


# --- Flask Routes ---

@app.route('/image_snapshot')
def image_snapshot():
    """
    Fetches the image, saves it locally, attempts to decode the barcode,
    and returns the image to the browser.
    """
    print("-" * 30)
    print(f"1. Attempting to fetch image from: {IMAGE_URL}")

    # 1. Fetch Image from ESP32-CAM
    try:
        response = requests.get(IMAGE_URL, timeout=10)
        response.raise_for_status()
        image_bytes = response.content
        print(f"2. Image fetched successfully. Size: {len(image_bytes)} bytes.")

    except requests.exceptions.RequestException as e:
        error_msg = f"FATAL ERROR: Could not fetch image from ESP32: {e}"
        print(error_msg)
        return Response(error_msg, status=500)

    # 2. Save Image Locally
    try:
        with open(OUTPUT_FILENAME, 'wb') as f:
            f.write(image_bytes)
        print(f"3. Image saved successfully as: {OUTPUT_FILENAME}")
    except Exception as e:
        print(f"ERROR: Could not save file {OUTPUT_FILENAME}: {e}")

    # 3. ATTEMPT BARCODE DECODING
    decode_saved_image(OUTPUT_FILENAME)  # <-- NEW FUNCTION CALL

    # 4. Return the raw image bytes to the browser for display
    return Response(image_bytes, mimetype='image/jpeg')


@app.route('/')
def index():
    """
    Renders a simple HTML page to display the captured image.
    """
    return render_template_string(f"""
    <html>
        <head>
            <title>ESP32-CAM Barcode Scanner</title>
            <style>
                body {{ font-family: sans-serif; text-align: center; }}
                img {{ max-width: 90%; border: 1px solid #ccc; margin-top: 20px; }}
            </style>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            <h1>ESP32-CAM Barcode Scanner</h1>
            <p>Refresh this page to capture a new image and attempt decoding.</p>
            <img src="/image_snapshot">
            <p style="margin-top: 30px; color: #555;">Check your Command Prompt console for the decoding result.</p>
        </body>
    </html>
    """)


if __name__ == '__main__':
    # Run the server, accessible from your local machine
    app.run(host='0.0.0.0', port=5000)
