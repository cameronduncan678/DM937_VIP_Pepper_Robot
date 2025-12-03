from flask import Flask, render_template, jsonify, abort, request, redirect
import json, os
from werkzeug.middleware.proxy_fix import ProxyFix

# ---------------------------------------------------------
# Allow importing helpers.py from the parent folder
# ---------------------------------------------------------
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from helper import search_product_by_name   # <-- uses CSV lookup


def create_app(config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # -----------------------------------------------------
    # App config
    # -----------------------------------------------------
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key'),
        PRODUCTS_FILE=os.path.join(app.root_path, 'data_products.json'),
        CSV_FILE=os.path.join(app.root_path, 'database/products.csv')
    )

    if config:
        app.config.update(config)

    # -----------------------------------------------------
    # ROUTES
    # -----------------------------------------------------

    @app.route('/')
    def index():
        return render_template('index.html')


    @app.route('/product', methods=['GET', 'POST'])
    def product_page():
        # data sent from index.html
        user_name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")

        result = None
        coords = None

        if request.method == 'POST':
            product_name = request.form.get("product")

            # Look up coords from CSV via helpers.py
            coords = search_product_by_name(product_name, app.config['CSV_FILE'])

            if coords:
                result = f"Product found! Coordinates: {coords}"
            else:
                result = f"Sorry, '{product_name}' was not found."

        return render_template(
            'product.html',
            name=user_name,
            allergy=allergy,
            result=result,
            coords=coords
        )


    # -----------------------------------------------------
    # SCAN BUTTON — run barcode.py and return to /product
    # -----------------------------------------------------
    @app.route('/scan', methods=['POST'])
    def scan():
        import subprocess
        import os

        barcode_script = os.path.join(app.root_path, "barcode.py")
        subprocess.Popen(["python3", barcode_script])   # run without waiting

        return redirect("/product")


    # -----------------------------------------------------
    # API – return entire JSON product file
    # -----------------------------------------------------
    @app.route('/api/products', methods=['GET'])
    def api_products():
        try:
            with open(app.config['PRODUCTS_FILE'], 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = []
        return jsonify({"products": data})


    # -----------------------------------------------------
    # API – get JSON product by ID
    # -----------------------------------------------------
    @app.route('/api/products/<int:product_id>', methods=['GET'])
    def api_product_detail(product_id):
        try:
            with open(app.config['PRODUCTS_FILE'], 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except FileNotFoundError:
            abort(404)

        for p in data:
            if p.get('id') == product_id:
                return jsonify(p)

        abort(404)


    # -----------------------------------------------------
    # Error Handler
    # -----------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    return app


# -----------------------------------------------------
# Run the Flask app
# -----------------------------------------------------
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
