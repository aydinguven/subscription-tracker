from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db, seed_default_categories
from app.models import User

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            # Seed default categories on first login
            seed_default_categories(user.id)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Self-registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        display_name = request.form.get('display_name', '').strip() or None
        
        if not username:
            flash('Username is required', 'error')
        elif len(username) < 3:
            flash('Username must be at least 3 characters', 'error')
        elif not password:
            flash('Password is required', 'error')
        elif len(password) < 4:
            flash('Password must be at least 4 characters', 'error')
        elif password != confirm:
            flash('Passwords do not match', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
        else:
            user = User(username=username, display_name=display_name, is_admin=False)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            seed_default_categories(user.id)
            login_user(user, remember=True)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard.index'))
    
    return render_template('register.html')


@bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('dashboard.index'))
