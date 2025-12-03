from flask import Flask, render_template, request, redirect
import os, csv, ast
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.wsgi_app = ProxyFix(app.wsgi_app)

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
    # SEARCH DATABASE FOR PRODUCT (RETURN CORDS)
    # -----------------------------------------------------
    
    def search_product_by_name(product_name, csv_file="database/products.csv"):
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["Name"].lower() == product_name.lower():
                    Xcoord = ast.literal_eval(row["X"])
                    Ycord = ast.literal_eval(row["Y"])
                    Zcord = ast.literal_eval(row["Z"])
                    return Xcoord, Ycord, Zcord
        return None

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
                result = f"Product found! Please follow Pepper Robot. (Coordinates: {coords})"
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


    return app


# -----------------------------------------------------
# Run the Flask app
# -----------------------------------------------------
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
