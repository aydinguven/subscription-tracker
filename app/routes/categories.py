from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Category

bp = Blueprint('categories', __name__)


@bp.route('/')
@login_required
def index():
    """List all categories."""
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template('categories.html', categories=categories)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add a new category."""
    if request.method == 'POST':
        name = request.form.get('name')
        color = request.form.get('color', '#6b7280')
        icon = request.form.get('icon', 'box')
        
        # Check for duplicate within user's categories
        if Category.query.filter_by(user_id=current_user.id, name=name).first():
            flash(f'Category "{name}" already exists!', 'error')
            return redirect(url_for('categories.add'))
        
        category = Category(user_id=current_user.id, name=name, color=color, icon=icon)
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{name}" added!', 'success')
        return redirect(url_for('categories.index'))
    
    return render_template('category_form.html', category=None, action='Add')


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit a category."""
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.color = request.form.get('color', '#6b7280')
        category.icon = request.form.get('icon', 'box')
        
        db.session.commit()
        flash(f'Category "{category.name}" updated!', 'success')
        return redirect(url_for('categories.index'))
    
    return render_template('category_form.html', category=category, action='Edit')


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a category."""
    category = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    name = category.name
    
    # Unlink subscriptions from this category
    for sub in category.subscriptions:
        sub.category_id = None
    
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{name}" deleted!', 'success')
    return redirect(url_for('categories.index'))
