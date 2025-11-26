from flask import Flask, render_template, jsonify, send_from_directory, abort
import json, os
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app(config=None):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.wsgi_app = ProxyFix(app.wsgi_app)

    # simple config
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-key'),
        PRODUCTS_FILE=os.path.join(app.root_path, 'data_products.json')
    )
    if config:
        app.config.update(config)

    @app.route('/')
    def index():
        return render_template('index.html')

    from flask import request  # make sure this is at the top

    @app.route('/product')
    def product_page():
        name = request.args.get("name", "there")
        allergy = request.args.get("allergy", "")
        return render_template('product.html', name=name, allergy=allergy)


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

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001, debug=True)
