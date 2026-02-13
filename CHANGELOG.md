# Changelog

## [1.2.0] - 2026-02-13

### Added
- **Multi-user authentication** — login system using Flask-Login with session management
- **User model** with username, password hashing (werkzeug), display name, and admin flag
- **Per-user data isolation** — `user_id` foreign key on all data models (subscriptions, payments, categories, payment methods, settings)
- **Login page** with glassmorphism design matching existing dark theme
- **Sidebar user info** — shows current username and logout button
- **User management scripts** for both Linux (`manage_users.sh`) and Windows (`manage_users.ps1`) with interactive menu: create, list, edit, delete, change password
- **Windows PowerShell scripts** — `setup.ps1`, `update.ps1`, `manage_users.ps1`, `uninstall.ps1`
- **Data migration script** (`scripts/migrate_data.py`) to assign existing records to a user after upgrade
- **Shared utilities module** (`app/utils.py`) with `parse_date()` function

### Changed
- All routes now require authentication via `@login_required`
- All database queries scoped to `current_user.id` for data isolation
- `Category` unique constraint changed from global to per-user `(user_id, name)`
- `PaymentMethod.is_default` logic is now per-user
- `Settings.get_settings()` now accepts and filters by `user_id`
- `setup.sh` now prompts for initial admin user creation during install
- `deploy.sh` and `update.sh` now copy `manage_users.sh` to install directory
- Scripts reorganized into `scripts/linux/` and `scripts/windows/` directories
- Removed duplicate `undeploy.sh` (merged into `uninstall.sh`)

### Security
- All routes (except `/api/health`) protected by authentication
- Password hashing with werkzeug PBKDF2
- User-scoped queries prevent cross-user data access
- `first_or_404()` used for single-record lookups with `user_id` guard

### Upgrade Notes
After updating to 1.2.0 on an existing deployment:
1. Run `scripts/linux/update.sh` (or git pull + pip install)
2. Create first user: `sudo /opt/subscription-tracker/manage_users.sh`
3. Migrate existing data: `python3 scripts/migrate_data.py`
4. Restart the service

## [1.1.0] - 2026-02-05

### Added
- Yearly report with stacked bar charts (monthly vs yearly subscriptions)
- Future month predictions with striped chart patterns
- Hide deactivated subscriptions by default

### Fixed
- Layout shift on HTMX page transitions
- Stable scrollbar-gutter to prevent content shifting
