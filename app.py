from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import tempfile
from datetime import datetime
from functools import wraps

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# Use temp directory for database
DATABASE = os.path.join(tempfile.gettempdir(), 'coco_store.db')

# Get the directory where this script is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'coco_household_store_secret_key_2024'

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

WHATSAPP_NUMBER = '+2348033939180'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_products'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

@app.route('/')
def index():
     db = get_db()
     products = db.execute('SELECT * FROM products LIMIT 8').fetchall()
     categories = db.execute('SELECT DISTINCT category FROM products').fetchall()
     return render_template('index.html', products=products, categories=[c[0] for c in categories])

@app.route('/products')
def products():
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

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if not product:
        flash('Product not found', 'error')
        return redirect(url_for('products'))
    return render_template('product_detail.html', product=product)

@app.route('/add_to_cart/<int:product_id>')
def add_to_cart(product_id):
    db = get_db()
    product = db.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
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

@app.route('/cart')
def cart():
    cart_items = session.get('cart', {})
    total = sum(item['price'] * item['quantity'] for item in cart_items.values())
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart/<int:product_id>', methods=['POST'])
def update_cart(product_id):
    quantity = int(request.form.get('quantity', 0))
    
    if 'cart' in session and str(product_id) in session['cart']:
        if quantity > 0:
            session['cart'][str(product_id)]['quantity'] = quantity
        else:
            del session['cart'][str(product_id)]
        session.modified = True
    
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session and str(product_id) in session['cart']:
        del session['cart'][str(product_id)]
        session.modified = True
        flash('Item removed from cart', 'success')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart_items = session.get('cart', {})
    
    if not cart_items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('products'))
    
    total = sum(item['price'] * item['quantity'] for item in cart_items.values())
    
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_phone = request.form.get('customer_phone')
        customer_address = request.form.get('customer_address')
        
        # Save order to database
        order_details = ', '.join([f"{item['name']} (x{item['quantity']})" for item in cart_items.values()])
        
        db = get_db()
        db.execute(
            'INSERT INTO orders (customer_name, customer_phone, customer_address, total_amount, order_details) VALUES (?, ?, ?, ?, ?)',
            (customer_name, customer_phone, customer_address, total, order_details)
        )
        db.commit()
        
        # Clear cart
        session.pop('cart', None)
        
        # Create WhatsApp message
        whatsapp_message = f"Hello! New order from {customer_name}%0APhone: {customer_phone}%0AAddress: {customer_address}%0AOrder: {order_details}%0ATotal: ₦{total:,.2f}%0A%0APlease provide payment instructions."
        
        return redirect(f"https://wa.me/{WHATSAPP_NUMBER}?text={whatsapp_message}")
    
    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/admin/orders')
@login_required
def admin_orders():
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/products')
@login_required
def admin_products():
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('admin_products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        category = request.form.get('category')
        image_url = request.form.get('image_url')
        stock = int(request.form.get('stock', 0))
        
        db = get_db()
        db.execute(
            'INSERT INTO products (name, description, price, category, image_url, stock) VALUES (?, ?, ?, ?, ?, ?)',
            (name, description, price, category, image_url, stock)
        )
        db.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin_add_product.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)