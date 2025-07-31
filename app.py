import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User, ParkingLot, ParkingSpot, Reservation
from database import init_app, db
from datetime import datetime
from collections import Counter
from sqlalchemy import func
from functools import wraps

# App Initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create admin user if not exists
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', is_admin=True)
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()

# --- Helper Functions ---
def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Main Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard') if current_user.is_admin else url_for('user_dashboard'))
    return redirect(url_for('login'))

# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'warning')
        else:
            new_user = User(username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Admin Routes ---
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    lots = ParkingLot.query.all()
    total_revenue = db.session.query(func.sum(Reservation.cost)).scalar() or 0.0
    return render_template('admin_dashboard.html', lots=lots, total_revenue=total_revenue)

@app.route('/admin/lot/create', methods=['GET', 'POST'])
@admin_required
def create_lot():
    if request.method == 'POST':
        try:
            name = request.form['name']
            price = float(request.form['price'])
            max_spots = int(request.form['max_spots'])

            if not name or price < 0 or max_spots <= 0:
                flash('Invalid data submitted. Please check your inputs.', 'danger')
                return render_template('create_lot.html')

            new_lot = ParkingLot(name=name, address=request.form['address'], pin_code=request.form['pin_code'], price=price, max_spots=max_spots)
            db.session.add(new_lot)
            db.session.flush()

            for i in range(1, max_spots + 1):
                spot = ParkingSpot(lot_id=new_lot.id, spot_number=i)
                db.session.add(spot)
            
            db.session.commit()
            flash('Parking lot created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except (ValueError, TypeError):
            flash('Invalid data format submitted.', 'danger')
    return render_template('create_lot.html')


@app.route('/admin/lot/edit/<int:lot_id>', methods=['GET', 'POST'])
@admin_required
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        try:
            new_max_spots = int(request.form['max_spots'])
            if new_max_spots < lot.spots.filter_by(status='O').count():
                flash('Cannot reduce spots below the number of currently occupied spots.', 'danger')
                return redirect(url_for('edit_lot', lot_id=lot.id))

            lot.name = request.form['name']
            lot.address = request.form['address']
            lot.pin_code = request.form['pin_code']
            lot.price = float(request.form['price'])

            if new_max_spots > lot.max_spots:
                for i in range(lot.max_spots + 1, new_max_spots + 1):
                    spot = ParkingSpot(lot_id=lot.id, spot_number=i)
                    db.session.add(spot)
            
            lot.max_spots = new_max_spots
            db.session.commit()
            flash('Lot updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except (ValueError, TypeError):
             flash('Invalid data format submitted.', 'danger')
    return render_template('edit_lot.html', lot=lot)

@app.route('/admin/lot/<int:lot_id>')
@admin_required
def lot_details(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('lot_details.html', lot=lot)

@app.route('/admin/lot/delete/<int:lot_id>', methods=['POST'])
@admin_required
def delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    if lot.spots.filter_by(status='O').count() > 0:
        flash('Cannot delete lot with occupied spots.', 'danger')
    else:
        db.session.delete(lot)
        db.session.commit()
        flash('Parking lot deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users')
@admin_required
def view_users():
    users = User.query.filter_by(is_admin=False).all()
    return render_template('view_users.html', users=users)

# --- User Routes ---
@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    
    lots = ParkingLot.query.all()
    for lot in lots:
        lot.available_spots = lot.spots.filter_by(status='A').count()

    return render_template('user_dashboard.html', lots=lots)

@app.route('/book/<int:lot_id>')
@login_required
def book_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    available_spot = lot.spots.filter_by(status='A').first()

    if available_spot:
        active_booking = Reservation.query.filter_by(user_id=current_user.id, leaving_time=None).first()
        if active_booking:
            flash(f'You already have an active booking.', 'warning')
            return redirect(url_for('booking_history'))

        available_spot.status = 'O'
        reservation = Reservation(spot_id=available_spot.id, user_id=current_user.id, parking_time=datetime.now())
        db.session.add(reservation)
        db.session.commit()
        flash(f'Successfully booked spot #{available_spot.spot_number} in {lot.name}!', 'success')
    else:
        flash(f'Sorry, no available spots in {lot.name}', 'danger')
    return redirect(url_for('user_dashboard'))

@app.route('/release/<int:reservation_id>')
@login_required
def release_spot(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != current_user.id:
        abort(403)
    
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'A'
    reservation.leaving_time = datetime.now()

    duration_hours = (reservation.leaving_time - reservation.parking_time).total_seconds() / 3600
    reservation.cost = round(duration_hours * spot.lot.price, 2)
    db.session.commit()
    flash(f'Spot released successfully! Total cost: ${reservation.cost}', 'success')
    return redirect(url_for('booking_history'))

@app.route('/history')
@login_required
def booking_history():
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.parking_time.desc()).all()
    return render_template('booking_history.html', reservations=reservations)

# --- API and Chart Data Routes ---
@app.route('/admin/chart-data')
@admin_required
def admin_chart_data():
    lots = ParkingLot.query.all()
    labels = [lot.name for lot in lots]
    occupied_data = [lot.spots.filter_by(status='O').count() for lot in lots]
    available_data = [lot.spots.filter_by(status='A').count() for lot in lots]

    return jsonify({'labels': labels, 'occupied': occupied_data, 'available': available_data})

@app.route('/user/chart-data')
@login_required
def user_chart_data():
    reservations = Reservation.query.filter_by(user_id=current_user.id).all()
    lot_names = [r.spot.lot.name for r in reservations if r.spot and r.spot.lot]
    lot_counts = Counter(lot_names)
    return jsonify({'labels': list(lot_counts.keys()), 'data': list(lot_counts.values())})

@app.route('/api/lots', methods=['GET'])
def get_lots():
    lots = ParkingLot.query.all()
    return jsonify([{'id': l.id, 'name': l.name, 'address': l.address, 'price': l.price, 'max_spots': l.max_spots} for l in lots])

@app.route('/api/lots/<int:lot_id>', methods=['GET'])
def get_lot_detail(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    occupied_spots = lot.spots.filter_by(status='O').count()
    return jsonify({'id': lot.id, 'name': lot.name, 'address': lot.address, 'price': lot.price, 'max_spots': lot.max_spots, 'occupied_spots': occupied_spots, 'available_spots': lot.max_spots - occupied_spots})

if __name__ == '__main__':
    app.run(debug=True)