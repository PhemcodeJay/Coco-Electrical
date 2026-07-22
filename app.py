from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from datetime import datetime
from functools import wraps
import logging
from werkzeug.exceptions import NotFound
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
SECRET_KEY = os.environ.get('SECRET_KEY', 'coco_household_store_secret_key_2024')
WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '+2348033939180')

# Email configuration
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '')

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

# Use application directory for database (persistent)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'instance', 'coco_store.db')

# Ensure instance and upload directories exist
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, UPLOAD_FOLDER), exist_ok=True)

# Get the directory where this script is located
app = Flask(__name__, 
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """Save an uploaded file and return the relative path."""
    if file and allowed_file(file.filename):
        # Generate a unique filename to prevent overwrites
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(BASE_DIR, UPLOAD_FOLDER, unique_filename)
        file.save(filepath)
        return f"uploads/{unique_filename}"
    return None

def send_order_email(customer_name, customer_phone, customer_address, order_details, total):
    """Send email notification about a new order."""
    if not MAIL_USERNAME or not MAIL_PASSWORD or not ADMIN_EMAIL:
        logger.warning("Email not configured. Skipping order notification email.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = ADMIN_EMAIL
        msg['Subject'] = f"New Order from {customer_name} - Coco Household Store"

        body = f"""
New Order Received!
====================

Customer Details:
-----------------
Name: {customer_name}
Phone: {customer_phone}
Address: {customer_address}

Order Summary:
--------------
{order_details}

Total Amount: ₦{total:,.2f}

Please process this order and contact the customer for payment.
        """

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_USE_TLS:
                server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"Order notification email sent to {ADMIN_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Failed to send order email: {e}")
        return False

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login to access admin area', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            image_url TEXT,
            stock INTEGER DEFAULT 0
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            total_amount REAL NOT NULL,
            order_details TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    db.commit()
    
    # Add sample products if not exist
    cursor = db.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ('Coco Blender Pro', 'High-power kitchen blender with multiple speed settings', 15000, 'Kitchen Appliances', 'https://picsum.photos/seed/blender/400/300', 10),
            ('Coco Microwave Oven', '20L digital microwave with grill function', 25000, 'Kitchen Appliances', 'https://picsum.photos/seed/microwave/400/300', 15),
            ('Coco Electric Kettle', 'Fast-boiling 1.7L electric kettle', 8500, 'Kitchen Appliances', 'https://picsum.photos/seed/kettle/400/300', 20),
            ('Coco Toaster', '4-slice pop-up toaster with browning control', 6500, 'Kitchen Appliances', 'https://picsum.photos/seed/toaster/400/300', 25),
            ('LED Ceiling Light', 'Energy-saving 15W LED ceiling light', 3500, 'Lighting', 'https://picsum.photos/seed/ceiling/400/300', 50),
            ('LED Bulb Pack', 'Pack of 4 LED bulbs (9W, B22)', 2000, 'Lighting', 'https://picsum.photos/seed/bulb/400/300', 100),
            ('Table Lamp', 'Modern design table lamp with USB charging', 4500, 'Lighting', 'https://picsum.photos/seed/lamp/400/300', 30),
            ('Coco Drill Machine', '10mm cordless drill with battery', 12000, 'Tools', 'https://picsum.photos/seed/drill/400/300', 15),
            ('Toolset 15pcs', 'Complete household toolset with case', 8000, 'Tools', 'https://picsum.photos/seed/tools/400/300', 20),
            ('Extension Cord 5m', 'Heavy-duty 5-meter extension cord', 3000, 'Accessories', 'https://picsum.photos/seed/cord/400/300', 50),
            ('Socket Outlets', 'Pack of 10 electrical sockets', 2500, 'Accessories', 'https://picsum.photos/seed/socket/400/300', 40),
            ('Mini Fridge', 'Compact 40L mini refrigerator', 35000, 'Refrigeration', 'https://picsum.photos/seed/fridge/400/300', 8),
        ]
        db.executemany('INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)', sample_products)
        db.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            logger.info(f"Admin login successful for user: {username}")
            return redirect(url_for('admin_products'))
        else:
            flash('Invalid credentials', 'error')
            logger.warning(f"Failed login attempt for user: {username}")
    
    return render_template('login.html', admin_username=ADMIN_USERNAME, admin_password=ADMIN_PASSWORD)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
    try:
        db = get_db()
        products = db.execute('SELECT * FROM products LIMIT 8').fetchall()
        categories = db.execute('SELECT DISTINCT category FROM products').fetchall()
        return render_template('index.html', products=products, categories=[c[0] for c in categories])
    except Exception as e:
        logger.error(f"Error in index page: {e}")
        flash('An error occurred', 'error')
        return render_template('index.html', products=[], categories=[])

@app.route('/products')
def products():
    try:
        db = get_db()
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        
        query = 'SELECT * FROM products'
        params = []
        
        if category:
            query += ' WHERE category = ?'
            params.append(category)
        elif search:
            query += ' WHERE name LIKE ? OR description LIKE ?'
            params.extend([f'%{search}%', f'%{search}%'])
        
        products = db.execute(query, params).fetchall()
        categories = db.execute('SELECT DISTINCT category FROM products').fetchall()
        return render_template('products.html', products=products, categories=[c[0] for c in categories], current_category=category, search=search)
    except Exception as e:
        logger.error(f"Error in products page: {e}")
        flash('An error occurred', 'error')
        return render_template('products.html', products=[], categories=[], current_category=None, search=None)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    try:
        db = get_db()
        product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('products'))
        return render_template('product_detail.html', product=product)
    except Exception as e:
        logger.error(f"Error in product detail page: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('products'))

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    try:
        db = get_db()
        product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('products'))
        
        if 'cart' not in session:
            session['cart'] = {}
        
        if str(product_id) in session['cart']:
            session['cart'][str(product_id)]['quantity'] += 1
        else:
            session['cart'][str(product_id)] = {
                'id': product_id,
                'name': product['name'],
                'price': product['price'],
                'image_url': product['image_url'],
                'quantity': 1
            }
        
        session.modified = True
        flash(f'{product["name"]} added to cart!', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('products'))

@app.route('/cart')
def cart():
    try:
        cart_items = session.get('cart', {})
        total = sum(item['price'] * item['quantity'] for item in cart_items.values())
        return render_template('cart.html', cart_items=cart_items, total=total)
    except Exception as e:
        logger.error(f"Error in cart page: {e}")
        flash('An error occurred', 'error')
        return render_template('cart.html', cart_items={}, total=0)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    try:
        quantity = int(request.form.get('quantity', 0))
        
        if 'cart' in session and str(product_id) in session['cart']:
            if quantity > 0:
                session['cart'][str(product_id)]['quantity'] = quantity
            else:
                del session['cart'][str(product_id)]
            session.modified = True
        
        return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Error updating cart: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    try:
        if 'cart' in session and str(product_id) in session['cart']:
            del session['cart'][str(product_id)]
            session.modified = True
            flash('Item removed from cart', 'success')
        return redirect(url_for('cart'))
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    try:
        cart_items = session.get('cart', {})
        
        if not cart_items:
            flash('Your cart is empty', 'error')
            return redirect(url_for('products'))
        
        total = sum(item['price'] * item['quantity'] for item in cart_items.values())
        
        if request.method == 'POST':
            customer_name = request.form.get('customer_name', '')
            customer_phone = request.form.get('customer_phone', '')
            customer_address = request.form.get('customer_address', '')
            
            # Validate required fields
            if not all([customer_name, customer_phone, customer_address]):
                flash('Please fill in all required fields', 'error')
                return render_template('checkout.html', cart_items=cart_items, total=total)
            
            # Save order to database
            order_details = ', '.join([f"{item['name']} (x{item['quantity']})" for item in cart_items.values()])
            
            db = get_db()
            db.execute(
                'INSERT INTO orders (customer_name, customer_phone, customer_address, total_amount, order_details) VALUES (?, ?, ?, ?, ?)',
                (customer_name, customer_phone, customer_address, total, order_details)
            )
            db.commit()
            
            # Send email notification to admin
            send_order_email(customer_name, customer_phone, customer_address, order_details, total)
            
            # Clear cart
            session.pop('cart', None)
            
            # Create WhatsApp message
            whatsapp_message = f"Hello! New order from {customer_name}%0APhone: {customer_phone}%0AAddress: {customer_address}%0AOrder: {order_details}%0ATotal: ₦{total:,.2f}%0A%0APlease provide payment instructions."
            
            logger.info(f"Order placed by {customer_name}")
            return redirect(f"https://wa.me/{WHATSAPP_NUMBER}?text={whatsapp_message}")
        
        return render_template('checkout.html', cart_items=cart_items, total=total)
    except Exception as e:
        logger.error(f"Error in checkout: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('products'))

@app.route('/admin/orders')
@login_required
def admin_orders():
    try:
        db = get_db()
        orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
        return render_template('admin_orders.html', orders=orders)
    except Exception as e:
        logger.error(f"Error in admin orders: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('index'))

@app.route('/admin/products')
@login_required
def admin_products():
    try:
        db = get_db()
        products = db.execute('SELECT * FROM products').fetchall()
        return render_template('admin_products.html', products=products)
    except Exception as e:
        logger.error(f"Error in admin products: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('index'))

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    try:
        if request.method == 'POST':
            name = request.form.get('name', '')
            description = request.form.get('description', '')
            price = float(request.form.get('price', 0))
            category = request.form.get('category', '')
            image_url = request.form.get('image_url', '')
            stock = int(request.form.get('stock', 0))
            
            # Handle file upload
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and file.filename:
                    uploaded_path = save_uploaded_file(file)
                    if uploaded_path:
                        image_url = uploaded_path
                    else:
                        flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp', 'error')
                        return render_template('admin_add_product.html')
            
            db = get_db()
            db.execute(
                'INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)',
                (name, description, price, category, image_url, stock)
            )
            db.commit()
            flash('Product added successfully!', 'success')
            logger.info(f"Product added: {name}")
            return redirect(url_for('admin_products'))
        
        return render_template('admin_add_product.html')
    except Exception as e:
        logger.error(f"Error adding product: {e}")
        flash('An error occurred', 'error')
        return render_template('admin_add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_product(product_id):
    try:
        db = get_db()
        product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('admin_products'))
        
        if request.method == 'POST':
            name = request.form.get('name', '')
            description = request.form.get('description', '')
            price = float(request.form.get('price', 0))
            category = request.form.get('category', '')
            image_url = request.form.get('image_url', '')
            stock = int(request.form.get('stock', 0))
            
            # Handle file upload - new image replaces old one
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and file.filename:
                    uploaded_path = save_uploaded_file(file)
                    if uploaded_path:
                        # Delete old image if it was a local upload
                        old_image = product['image_url']
                        if old_image and not old_image.startswith('http'):
                            old_path = os.path.join(BASE_DIR, 'static', old_image)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                                logger.info(f"Deleted old image: {old_image}")
                        image_url = uploaded_path
                    else:
                        flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp', 'error')
                        return render_template('admin_edit_product.html', product=product)
            
            db.execute(
                'UPDATE products SET name=?, description=?, price=?, category=?, image_url=?, stock=? WHERE id=?',
                (name, description, price, category, image_url, stock, product_id)
            )
            db.commit()
            flash('Product updated successfully!', 'success')
            logger.info(f"Product updated: {name} (ID: {product_id})")
            return redirect(url_for('admin_products'))
        
        return render_template('admin_edit_product.html', product=product)
    except Exception as e:
        logger.error(f"Error editing product {product_id}: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('admin_products'))

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@login_required
def admin_delete_product(product_id):
    try:
        db = get_db()
        product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
        
        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('admin_products'))
        
        # Delete the product image if it's a local upload
        image_url = product['image_url']
        if image_url and not image_url.startswith('http'):
            image_path = os.path.join(BASE_DIR, 'static', image_url)
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info(f"Deleted image: {image_url}")
        
        db.execute('DELETE FROM products WHERE id = ?', (product_id,))
        db.commit()
        flash(f'Product "{product["name"]}" deleted successfully!', 'success')
        logger.info(f"Product deleted: {product['name']} (ID: {product_id})")
        return redirect(url_for('admin_products'))
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        flash('An error occurred', 'error')
        return redirect(url_for('admin_products'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    init_db()
    # Development server only - use gunicorn for production
    app.run(host='0.0.0.0', port=5000, debug=False)