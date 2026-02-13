#!/usr/bin/env python3
"""
Migration script: Assign existing data to a user.

Run this after upgrading to the multi-user version to assign all
existing records (that have no user_id) to a specific user.

Usage:
    python3 migrate_data.py [--user-id N]
    
If --user-id is not specified, the first user in the database is used.
If no users exist, you'll be prompted to create one.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db, seed_default_categories
from app.models import User, Category, PaymentMethod, Subscription, Payment, Settings


def migrate(user_id=None):
    app = create_app()
    
    with app.app_context():
        # Find or select user
        if user_id:
            user = User.query.get(user_id)
            if not user:
                print(f"ERROR: No user with ID {user_id}")
                sys.exit(1)
        else:
            user = User.query.first()
        
        if not user:
            print("No users exist. Please create a user first with manage_users.sh")
            print("Or run: python3 -c \"from app import create_app, db; from app.models import User; app = create_app(); ...")
            sys.exit(1)
        
        print(f"Migrating data to user: {user.username} (ID: {user.id})")
        
        # Count orphaned records
        orphan_cats = Category.query.filter_by(user_id=None).count()
        orphan_methods = PaymentMethod.query.filter_by(user_id=None).count()
        orphan_subs = Subscription.query.filter_by(user_id=None).count()
        orphan_payments = Payment.query.filter_by(user_id=None).count()
        orphan_settings = Settings.query.filter_by(user_id=None).count()
        
        total = orphan_cats + orphan_methods + orphan_subs + orphan_payments + orphan_settings
        
        if total == 0:
            print("No orphaned records found. Nothing to migrate.")
            return
        
        print(f"\nRecords to migrate:")
        print(f"  Categories:       {orphan_cats}")
        print(f"  Payment Methods:  {orphan_methods}")
        print(f"  Subscriptions:    {orphan_subs}")
        print(f"  Payments:         {orphan_payments}")
        print(f"  Settings:         {orphan_settings}")
        print(f"  Total:            {total}")
        
        # Perform migration
        Category.query.filter_by(user_id=None).update({'user_id': user.id})
        PaymentMethod.query.filter_by(user_id=None).update({'user_id': user.id})
        Subscription.query.filter_by(user_id=None).update({'user_id': user.id})
        Payment.query.filter_by(user_id=None).update({'user_id': user.id})
        Settings.query.filter_by(user_id=None).update({'user_id': user.id})
        
        db.session.commit()
        
        print(f"\n✓ Successfully migrated {total} records to user '{user.username}'")


if __name__ == '__main__':
    target_user_id = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--user-id' and i + 1 < len(args):
            target_user_id = int(args[i + 1])
            i += 2
        elif args[i] in ('-h', '--help'):
            print(__doc__)
            sys.exit(0)
        else:
            print(f"Unknown argument: {args[i]}")
            sys.exit(1)
    
    migrate(target_user_id)
