import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DATABASE = 'food_waste.db'

# Function to get a connection to the SQLite database
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Create the tables if they don't already exist
def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS inventory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        restaurant_name TEXT NOT NULL,
                        address TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        location TEXT NOT NULL,
                        food_item TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        expiration_date TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS contact_queries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        message TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL,
                        feedback TEXT NOT NULL,
                        category TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS admin (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        otp TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        restaurant_name TEXT NOT NULL,
                        order_id TEXT NOT NULL,
                        food_item TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        status TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS donations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        restaurant_name TEXT NOT NULL,
                        donation_id TEXT NOT NULL,
                        food_item TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        recipient TEXT NOT NULL)''')
    conn.commit()
    conn.close()

# Home page route
@app.route('/')
def home():
    return render_template('index.html')

# Inventory page route
@app.route('/inventory')
def inventory():
    conn = get_db()
    query = '''
        SELECT * FROM inventory WHERE expiration_date <= date('now', '+7 days') ORDER BY expiration_date
    '''
    items = conn.execute(query).fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

# Route to add new inventory item
@app.route('/add_inventory', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        restaurant_name = request.form['restaurant_name']
        address = request.form['address']
        phone_number = request.form['phone_number']
        location = request.form['location']
        food_item = request.form['food_item']
        quantity = request.form['quantity']
        expiration_date = request.form['expiration_date']

        # Connect to database and insert the inventory details
        conn = get_db()
        conn.execute('INSERT INTO inventory (restaurant_name, address, phone_number, location, food_item, quantity, expiration_date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (restaurant_name, address, phone_number, location, food_item, quantity, expiration_date))
        conn.commit()
        conn.close()

        # Redirect to the inventory page after successfully adding the item
        return redirect(url_for('inventory'))
    
    return render_template('add_inventory.html')


# Route for feedback form
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        user_name = request.form['name']
        user_email = request.form['email']
        user_feedback = request.form['feedback']
        feedback_category = request.form['category']  # Added field for category
        
        conn = get_db()
        conn.execute('INSERT INTO feedback (name, email, feedback, category) VALUES (?, ?, ?, ?)',
                     (user_name, user_email, user_feedback, feedback_category))
        conn.commit()
        conn.close()
        return redirect(url_for('feedback'))

    conn = get_db()
    feedback_items = conn.execute('SELECT * FROM feedback').fetchall()
    conn.close()

    return render_template('feedback.html', feedback_items=feedback_items)

# Route for contact page
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        conn = get_db()
        conn.execute('INSERT INTO contact_queries (name, email, message) VALUES (?, ?, ?)',
                     (name, email, message))
        conn.commit()
        conn.close()
        return redirect(url_for('contact'))

    return render_template('contact.html')

# About Us page route
@app.route('/about')
def about():
    return render_template('about.html')

# Admin login route
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        if email == 'admin@example.com':
            otp = str(random.randint(1000, 9999))
            conn = get_db()
            conn.execute('INSERT INTO admin (email, otp) VALUES (?, ?)', (email, otp))
            conn.commit()
            conn.close()
            session['admin_email'] = email
            return render_template('otp_verification.html', email=email)
        else:
            return 'Unauthorized access'
    return render_template('admin_login.html')

# OTP verification route
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    entered_otp = request.form['otp']
    conn = get_db()
    query = conn.execute('SELECT otp FROM admin WHERE email = ?', (session['admin_email'],))
    stored_otp = query.fetchone()
    conn.close()

    if stored_otp and stored_otp['otp'] == entered_otp:
        return redirect(url_for('admin_page'))
    else:
        return 'Invalid OTP'

# Admin page to view all inventories, feedback, contact queries, orders, donations, etc.
@app.route('/admin_page')
def admin_page():
    conn = get_db()
    inventories = conn.execute('SELECT * FROM inventory').fetchall()
    feedbacks = conn.execute('SELECT * FROM feedback').fetchall()
    contact_queries = conn.execute('SELECT * FROM contact_queries').fetchall()
    orders = conn.execute('SELECT * FROM orders').fetchall()
    donations = conn.execute('SELECT * FROM donations').fetchall()
    conn.close()

    return render_template('admin_page.html', inventories=inventories, feedbacks=feedbacks,
                           contact_queries=contact_queries, orders=orders, donations=donations)

# Chatbot page route
@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        user_input = request.form['user_input'].lower()
        response = handle_user_input(user_input)
        return render_template('chatbot.html', response=response)
    return render_template('chatbot.html', response=None)

def handle_user_input(user_input):
    greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good evening']
    farewell = ['bye', 'goodbye', 'see you', 'take care']
    
    if any(greet in user_input for greet in greetings):
        return "Hello! How can I assist you today? Feel free to ask about inventory, orders, donations, or food waste management."
    
    if any(fare in user_input for fare in farewell):
        return "Goodbye! Hope to talk to you soon. Take care!"

    # Help section
    if 'help' in user_input:
        return """
            I can help you with the following tasks:
            - Managing inventory
            - Suggesting recipes based on available ingredients
            - Tracking and managing donations
            - Reporting and managing food waste
            - Managing orders
            - Providing sustainability tips
            - Reporting expired or near-expiry items
            - Providing contact and feedback forms for your business
            """

    if 'inventory' in user_input:
        return "You can view or manage inventory items on our inventory page. Do you want to add a new item or check stock levels?"

    if 'order' in user_input:
        return "You can check or manage orders through our orders section. Would you like to see current orders or add a new one?"

    if 'donation' in user_input:
        return "You can view and track donations on the donations page. Would you like to donate any food items today?"

    if 'waste' in user_input:
        return "You can report waste and suggest strategies to minimize it through our waste reporting section. Would you like tips on reducing food waste?"

    if 'sustainability' in user_input:
        return "We promote sustainability by reducing energy consumption, sourcing locally, and using eco-friendly packaging. Let's reduce food waste together!"

    if 'expired' in user_input or 'near expiry' in user_input:
        return "I can help you identify food items that are near expiry. Would you like me to check your inventory for items that need attention?"

    return "I didn’t quite understand that. Try asking me for help, or check out our pages for more details!"

# Sustainability page route
@app.route('/sustainability')
def sustainability():
    tips = [
        "Track your inventory regularly to prevent overstocking.",
        "Use FIFO (First In, First Out) to ensure older items are used first.",
        "Consider donating excess food to local charities.",
        "Offer daily specials using ingredients nearing expiration.",
        "Consider using biodegradable packaging to reduce waste."
    ]
    return render_template('sustainability.html', tips=tips)

# Route to send email notifications for food expiry
def send_email_notification(to_email, subject, body):
    message = Mail(
        from_email='no-reply@example.com',
        to_emails=to_email,
        subject=subject,
        plain_text_content=body)
    try:
        sg = SendGridAPIClient('your_sendgrid_api_key_here')
        sg.send(message)
    except Exception as e:
        print(str(e))

# Cron job or scheduled task to check for expirations
@app.route('/check_expirations')
def check_expirations():
    conn = get_db()
    items = conn.execute('SELECT * FROM inventory WHERE expiration_date <= date("now", "+7 days")').fetchall()
    conn.close()
    
    for item in items:
        send_email_notification(item['restaurant_email'], f"Urgent: {item['food_item']} is nearing expiration", 
                                f"The food item {item['food_item']} is nearing expiration on {item['expiration_date']}. Please take action to reduce food waste.")
    return "Expiry check complete"

# Run the app
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
