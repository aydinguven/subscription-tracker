import io
import json
from app.models import Subscription, Category, PaymentMethod


def test_json_export_and_import(auth_client, app, auth_user):
    """Test full round-trip JSON export and import."""
    # Create subscription
    auth_client.post('/subscriptions/add', data={
        'name': 'Spotify Family',
        'amount': '64.99',
        'currency': 'TRY',
        'billing_cycle': 'monthly',
        'next_due_date': '2026-09-15'
    })

    # Export JSON
    response = auth_client.post('/data/export', data={
        'format': 'json',
        'categories': 'on',
        'payment_methods': 'on',
        'subscriptions': 'on',
        'payments': 'on'
    })

    assert response.status_code == 200
    export_json = json.loads(response.data)
    assert 'subscriptions' in export_json
    assert any(s['name'] == 'Spotify Family' for s in export_json['subscriptions'])

    # Test re-import
    json_bytes = io.BytesIO(response.data)
    import_response = auth_client.post('/data/import', data={
        'file': (json_bytes, 'backup.json'),
        'skip_existing': 'on'
    }, follow_redirects=True)

    assert import_response.status_code == 200


def test_csv_export(auth_client, app, auth_user):
    """Test CSV export generation."""
    auth_client.post('/subscriptions/add', data={
        'name': 'GitHub Pro',
        'amount': '4.00',
        'currency': 'USD',
        'billing_cycle': 'monthly'
    })

    response = auth_client.post('/data/export', data={
        'format': 'csv',
        'subscriptions': 'on'
    })

    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert b'GitHub Pro' in response.data


def test_excel_export(auth_client, app, auth_user):
    """Test Excel (.xlsx) workbook export generation."""
    response = auth_client.post('/data/export', data={
        'format': 'excel',
        'categories': 'on',
        'payment_methods': 'on',
        'subscriptions': 'on',
        'payments': 'on'
    })

    assert response.status_code == 200
    assert 'spreadsheetml' in response.mimetype
