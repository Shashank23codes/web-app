from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from config import Config
from functools import wraps
from flask import Blueprint
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize MySQL
mysql = MySQL(app)

# Group related routes using Blueprints
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
donor_bp = Blueprint('donor', __name__, url_prefix='/donor')
ngo_bp = Blueprint('ngo', __name__, url_prefix='/ngo')
volunteer_bp = Blueprint('volunteer', __name__, url_prefix='/volunteer')

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(donor_bp)
app.register_blueprint(ngo_bp)
app.register_blueprint(volunteer_bp)

# Utility functions
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/')
def index():
    # Get user counts for each type
    cur = mysql.connection.cursor()
    cur.execute("SELECT user_type, COUNT(*) FROM users GROUP BY user_type")
    user_counts = dict(cur.fetchall())
    cur.close()
    
    return render_template('index.html', 
                         donor_count=user_counts.get('donor', 0),
                         ngo_count=user_counts.get('ngo', 0),
                         volunteer_count=user_counts.get('volunteer', 0))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        mobile = request.form['mobile']
        password = generate_password_hash(request.form['password'])
        user_type = request.form['user_type']
        
        cur = mysql.connection.cursor()
        
        # Check if email already exists
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        
        if user:
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
        
        # Insert user
        cur.execute("INSERT INTO users(username, email, mobile, password, user_type) VALUES(%s, %s, %s, %s, %s)",
                   (username, email, mobile, password, user_type))
        mysql.connection.commit()
        cur.close()
        
        flash('Registration successful! Please login', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", [email])
        user = cur.fetchone()
        cur.close()
        
        if user:
            password_hash = user[4]  # Stored hashed password
            if check_password_hash(password_hash, password_candidate):  # Corrected password verification
                session['logged_in'] = True
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['user_type'] = user[5]
                
                flash('You are now logged in', 'success')

                # Redirect based on user type
                if session['user_type'] == 'donor':
                    return redirect(url_for('donor_dashboard'))
                elif session['user_type'] == 'ngo':
                    return redirect(url_for('ngo_dashboard'))
                elif session['user_type'] == 'volunteer':
                    return redirect(url_for('volunteer_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                error = 'Invalid password'
                return render_template('login.html', error=error)
        else:
            error = 'Email not registered'
            return render_template('login.html', error=error)
    
    return render_template('login.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        secret_key = request.form['secret_key']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username = %s AND password = %s AND secret_key = %s", 
                    [username, password, secret_key])
        admin = cur.fetchone()
        
        if admin:
            logger.info("Admin login successful")
            session['admin_logged_in'] = True
            session['admin_id'] = admin[0]
            session['admin_username'] = admin[1]
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
        
        cur.close()
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if admin is logged in
    if not session.get('admin_logged_in'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    
    # Fetch donation requests
    cur.execute("""
        SELECT dr.id, dr.status, d.food_type, d.quantity, d.expiration_date, 
               d.pickup_location, dr.ngo_address, dr.reason, 
               u1.username as donor_name, u2.username as ngo_name
        FROM donation_requests dr
        JOIN donations d ON dr.donation_id = d.id
        JOIN users u1 ON d.donor_id = u1.id
        JOIN users u2 ON dr.ngo_id = u2.id
        ORDER BY dr.created_at DESC
    """)
    donation_requests = cur.fetchall()
    
    # Fetch all users
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    
    # Fetch all donations
    cur.execute("SELECT * FROM donations")
    donations = cur.fetchall()
    
    cur.close()
    
    return render_template('admin/dashboard.html', 
                         donation_requests=donation_requests, 
                         users=users, 
                         donations=donations)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('admin_logged_in'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    try:
        # Delete related records first
        cur.execute("DELETE FROM donation_requests WHERE volunteer_id = %s OR ngo_id = %s", 
                   [user_id, user_id])
        cur.execute("DELETE FROM donations WHERE donor_id = %s", [user_id])
        cur.execute("DELETE FROM users WHERE id = %s", [user_id])
        mysql.connection.commit()
        flash('User deleted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error deleting user', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('admin_dashboard'))

# Protected routes for different user types
@app.route('/donor/dashboard')
@is_logged_in
def donor_dashboard():
    if session['user_type'] != 'donor':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM donations WHERE donor_id = %s", [session['user_id']])
    donations = cur.fetchall()
    cur.close()
    
    return render_template('donor/dashboard.html', donations=donations)

@app.route('/donor/create_donation', methods=['POST'])
@is_logged_in
def create_donation():
    if session['user_type'] != 'donor':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        food_type = request.form['food_type']
        quantity = request.form['quantity']
        expiration_date = request.form['expiration_date']
        food_condition = request.form['food_condition']
        pickup_location = request.form['pickup_location']
        
        # Handle file upload
        food_image = None
        if 'food_image' in request.files:
            file = request.files['food_image']
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                food_image = filename
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO donations
            (donor_id, food_type, quantity, expiration_date, food_condition, pickup_location, food_image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], food_type, quantity, expiration_date, food_condition, pickup_location, food_image))
        mysql.connection.commit()
        cur.close()
        
        flash('Donation created successfully', 'success')
        return redirect(url_for('donor_dashboard'))
    
    return redirect(url_for('donor_dashboard'))

@app.route('/ngo/dashboard')
@is_logged_in
def ngo_dashboard():
    if session['user_type'] != 'ngo':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.*, u.username as donor_name 
        FROM donations d 
        JOIN users u ON d.donor_id = u.id 
        WHERE d.status = 'pending'
        ORDER BY d.created_at DESC
    """)
    available_donations = cur.fetchall()
    
    # Fetch rejected requests
    cur.execute("""
        SELECT 
            d.food_type,
            d.quantity,
            u.username as volunteer_name,
            dr.rejection_reason,
            dr.rejection_images,
            dr.created_at as rejected_at
        FROM donation_requests dr
        JOIN donations d ON dr.donation_id = d.id
        JOIN users u ON dr.volunteer_id = u.id
        WHERE dr.ngo_id = %s AND dr.status = 'rejected'
        ORDER BY dr.created_at DESC
    """, [session['user_id']])
    
    rejected_requests = [dict(zip([column[0] for column in cur.description], row)) 
                        for row in cur.fetchall()]
    
    cur.close()
    
    return render_template('ngo/dashboard.html', 
                         donations=available_donations,
                         rejected_requests=rejected_requests)

@app.route('/volunteer/dashboard')
@is_logged_in
def volunteer_dashboard():
    if session.get('user_type') != 'volunteer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    
    # Fetch all pending requests AND requests assigned to the current volunteer
    cur.execute("""
        SELECT 
            dr.id,
            dr.status as request_status,
            dr.ngo_address,
            dr.reason,
            d.pickup_location,
            d.food_type,
            d.quantity,
            d.expiration_date,
            u1.username as donor_name,
            u2.username as ngo_name,
            d.status as donation_status,
            dr.created_at
        FROM donation_requests dr 
        JOIN donations d ON dr.donation_id = d.id 
        JOIN users u1 ON d.donor_id = u1.id 
        JOIN users u2 ON dr.ngo_id = u2.id 
        WHERE (
            (dr.status = 'pending')  # Show all pending requests
            OR (dr.volunteer_id = %s)  # Show requests assigned to the current volunteer
        )
        ORDER BY dr.created_at DESC
    """, [session['user_id']])
    
    columns = [desc[0] for desc in cur.description]
    requests = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    
    # Debugging: Print fetched data
    print("Fetched requests for volunteer ID", session['user_id'], ":", requests)
    
    return render_template('volunteer/dashboard.html', requests=requests)

@app.route('/ngo/accept_donation', methods=['POST'])
@is_logged_in
def accept_donation():
    if session['user_type'] != 'ngo':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        donation_id = request.form['donation_id']
        ngo_address = request.form['ngo_address']
        reason = request.form['reason']
        
        cur = mysql.connection.cursor()
        
        # Find an available volunteer
        cur.execute("SELECT id FROM users WHERE user_type = 'volunteer' ORDER BY RAND() LIMIT 1")
        volunteer = cur.fetchone()
        
        # Print debug information
        print(f"Selected volunteer ID: {volunteer[0] if volunteer else None}")
        
        if not volunteer:
            flash('No volunteers available', 'danger')
            return redirect(url_for('ngo_dashboard'))
        
        try:
            # Create donation request
            cur.execute("""
                INSERT INTO donation_requests
                (donation_id, ngo_id, volunteer_id, ngo_address, reason)
                VALUES (%s, %s, %s, %s, %s)
            """, (donation_id, session['user_id'], volunteer[0], ngo_address, reason))
            
            # Update donation status
            cur.execute("UPDATE donations SET status = 'accepted' WHERE id = %s", [donation_id])
            
            mysql.connection.commit()
            print("Donation request created successfully")
            
            flash('Donation accepted successfully', 'success')
        except Exception as e:
            print(f"Error creating donation request: {str(e)}")
            mysql.connection.rollback()
            flash('Error accepting donation', 'danger')
        finally:
            cur.close()
        
        return redirect(url_for('ngo_dashboard'))
    
    return redirect(url_for('ngo_dashboard'))

@app.route('/volunteer/accept_request', methods=['POST'])
@is_logged_in
def accept_request():
    if session.get('user_type') != 'volunteer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    request_id = request.form['request_id']
    cur = mysql.connection.cursor()
    try:
        # Update the status to 'accepted' and set the volunteer_id
        cur.execute("""
            UPDATE donation_requests 
            SET status = 'accepted', volunteer_id = %s 
            WHERE id = %s
        """, [session['user_id'], request_id])
        mysql.connection.commit()
        flash('Request accepted successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error accepting request: ' + str(e), 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('volunteer_dashboard'))

@app.route('/volunteer/update_progress', methods=['POST'])
@is_logged_in
def update_progress():
    if session.get('user_type') != 'volunteer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    request_id = request.form['request_id']
    cur = mysql.connection.cursor()
    try:
        # Update the status to 'picked_up'
        cur.execute("""
            UPDATE donation_requests 
            SET status = 'picked_up' 
            WHERE id = %s
        """, [request_id])
        mysql.connection.commit()
        flash('Progress updated to "Picked Up"!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error updating progress: ' + str(e), 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('volunteer_dashboard'))

@app.route('/volunteer/update_delivery_status', methods=['POST'])
@is_logged_in
def update_delivery_status():
    if session.get('user_type') != 'volunteer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    request_id = request.form['request_id']
    cur = mysql.connection.cursor()
    try:
        # Update the status to 'completed'
        cur.execute("""
            UPDATE donation_requests 
            SET status = 'completed' 
            WHERE id = %s
        """, [request_id])
        mysql.connection.commit()
        flash('Delivery status updated to "Completed"!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('Error updating delivery status: ' + str(e), 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('volunteer_dashboard'))

@app.route('/volunteer/reject_request', methods=['POST'])
@is_logged_in
def reject_request():
    if session.get('user_type') != 'volunteer':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    request_id = request.form['request_id']
    reason = request.form['reason']
    
    # Handle image uploads
    image_filenames = []
    if 'images' in request.files:
        files = request.files.getlist('images')
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filenames.append(filename)
    
    cur = mysql.connection.cursor()
    try:
        # First update the status and basic details
        cur.execute("""
            UPDATE donation_requests 
            SET status = 'rejected', 
                rejection_reason = %s,
                rejection_images = %s
            WHERE id = %s
        """, [reason, ','.join(image_filenames) if image_filenames else None, request_id])
        
        # Then update the rejection details
        cur.execute("""
            UPDATE donation_requests 
            SET rejected_at = CURRENT_TIMESTAMP,
                rejected_by = %s
            WHERE id = %s
        """, [session['user_id'], request_id])
        
        # Update the donation status back to pending
        cur.execute("""
            UPDATE donations d
            JOIN donation_requests dr ON d.id = dr.donation_id
            SET d.status = 'pending'
            WHERE dr.id = %s
        """, [request_id])
        
        mysql.connection.commit()
        flash('Delivery request rejected successfully', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error rejecting request: {str(e)}', 'danger')
        print(f"Database error: {str(e)}")  # Add this for debugging
    finally:
        cur.close()
    
    return redirect(url_for('volunteer_dashboard'))

@app.route('/logout')
def logout():
    # Clear all session data
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

@app.route('/ngo/accepted_donations')
@is_logged_in
def accepted_donations():
    if session['user_type'] != 'ngo':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT d.food_type, d.quantity, d.expiration_date, d.pickup_location, 
               dr.ngo_address, dr.reason, dr.status, dr.created_at
        FROM donations d
        JOIN donation_requests dr ON d.id = dr.donation_id
        WHERE dr.ngo_id = %s AND dr.status = 'accepted'
        ORDER BY dr.created_at DESC
    """, [session['user_id']])
    
    accepted_donations = cur.fetchall()
    cur.close()
    
    return render_template('ngo/accepted_donations.html', donations=accepted_donations)

@app.route('/ngo/received_donations')
@is_logged_in
def received_donations():
    if session['user_type'] != 'ngo':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT dr.id, d.food_type, d.quantity, d.expiration_date, d.pickup_location, 
               dr.ngo_address, dr.reason, dr.status, dr.created_at, dr.feedback_given
        FROM donations d
        JOIN donation_requests dr ON d.id = dr.donation_id
        WHERE dr.ngo_id = %s
        ORDER BY dr.created_at DESC
    """, [session['user_id']])
    
    received_donations = cur.fetchall()
    cur.close()
    
    return render_template('ngo/received_donations.html', 
                         donations=received_donations)

@app.route('/ngo/submit_feedback', methods=['POST'])
@is_logged_in
def submit_feedback():
    if session['user_type'] != 'ngo':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    try:
        donation_request_id = request.form['donation_request_id']
        rating = int(request.form['rating'])
        comment = request.form['comment']
        
        if not (1 <= rating <= 5):
            flash('Rating must be between 1 and 5', 'danger')
            return redirect(url_for('received_donations'))
            
        if not comment or not rating:
            flash('Please provide both rating and comment', 'danger')
            return redirect(url_for('received_donations'))
        
        cur = mysql.connection.cursor()
        
        # Check if feedback already exists
        cur.execute("SELECT id FROM feedback WHERE donation_request_id = %s", [donation_request_id])
        if cur.fetchone():
            flash('Feedback already submitted for this donation', 'warning')
            return redirect(url_for('received_donations'))
        
        # Get donor_id from donation request
        cur.execute("SELECT donor_id FROM donations d JOIN donation_requests dr ON d.id = dr.donation_id WHERE dr.id = %s", [donation_request_id])
        donor = cur.fetchone()
        
        if not donor:
            flash('Invalid donation request', 'danger')
            return redirect(url_for('received_donations'))
        
        # Insert feedback
        cur.execute("""
            INSERT INTO feedback 
            (donation_request_id, ngo_id, donor_id, rating, comment)
            VALUES (%s, %s, %s, %s, %s)
        """, (donation_request_id, session['user_id'], donor[0], rating, comment))
        
        # Mark feedback as given
        cur.execute("UPDATE donation_requests SET feedback_given = TRUE WHERE id = %s", [donation_request_id])
        
        mysql.connection.commit()
        print(f"Inserting feedback: {donation_request_id}, {session['user_id']}, {donor[0]}, {rating}, {comment}")
        print(f"Feedback submitted for request {donation_request_id} by NGO {session['user_id']}")
        flash('Feedback submitted successfully!', 'success')
    except ValueError:
        flash('Invalid rating value', 'danger')
        return redirect(url_for('received_donations'))
    except Exception as e:
        flash(f'Error submitting feedback: {str(e)}', 'danger')
        return redirect(url_for('received_donations'))
    finally:
        cur.close()
    
    # Always return a response
    return redirect(url_for('received_donations'))

@app.route('/donor/feedback')
@is_logged_in
def donor_feedback():
    if session['user_type'] != 'donor':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT f.rating, f.comment, f.created_at, u.username as ngo_name
        FROM feedback f
        JOIN users u ON f.ngo_id = u.id
        WHERE f.donor_id = %s
        ORDER BY f.created_at DESC
    """, [session['user_id']])
    
    feedbacks = cur.fetchall()
    cur.close()
    
    # Add detailed logging
    print(f"Fetched feedback for donor {session['user_id']}:")
    for feedback in feedbacks:
        print(f"Rating: {feedback[0]}, Comment: {feedback[1]}, Date: {feedback[2]}, NGO: {feedback[3]}")
    
    return render_template('donor/feedback.html', feedbacks=feedbacks)

def update_request_status(request_id, status):
    cur = mysql.connection.cursor()
    try:
        cur.execute("UPDATE donation_requests SET status = %s WHERE id = %s", (status, request_id))
        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error updating request status: {e}")  # Debugging line
    finally:
        cur.close()

# Add error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    try:
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            return datetime.strptime(value, '%Y-%m-%d %H:%M:%S').strftime(format)
        elif isinstance(value, datetime):
            return value.strftime(format)
        return 'N/A'
    except Exception as e:
        logger.error(f"Error formatting datetime: {str(e)}")
        return 'N/A'

if __name__ == '__main__':
    app.run(debug=True)