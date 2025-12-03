from flask import Flask, render_template, jsonify, send_from_directory, abort, request
import json, os, csv, ast
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app(config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # simple config
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key'),
        PRODUCTS_FILE=os.path.join(app.root_path, 'data_products.json'),
        CSV_FILE=os.path.join(app.root_path, 'database/products.csv')   # <-- Your CSV file
    )
    if config:
        app.config.update(config)

    # -----------------------------------------------------
    # Helper function: Read coords "[x, y, theta]" from CSV
    # -----------------------------------------------------
    def search_product_by_name(name):
        try:
            with open(app.config['CSV_FILE'], newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row["Name"].lower() == name.lower():
                        # Convert string "[x, y, theta]" → real Python list
                        return ast.literal_eval(row["Location"])
        except FileNotFoundError:
            return None

        return None


    # ---------------------------
    # Routes
    # ---------------------------

    @app.route('/')
    def index():
        return render_template('index.html')


    @app.route('/product', methods=['GET', 'POST'])
    def product_page():
        # Get name + allergy passed from index.html
        user_name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")

        result = None
        coords = None

        if request.method == 'POST':
            product_name = request.form.get("product")

            # Look up product coordinates
            coords = search_product_by_name(product_name)

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


    # Existing API routes (unchanged)
    @app.route('/api/products', methods=['GET'])
    def api_products():
        try:
            with open(app.config['PRODUCTS_FILE'], 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = []
        return jsonify({"products": data})


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


    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    return app


# Run app
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
