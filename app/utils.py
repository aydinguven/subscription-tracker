"""Shared utility functions for the application."""

from datetime import date, datetime


def parse_date(date_string):
    """Parse date string from various formats.
    
    Supports:
    - ISO format: YYYY-MM-DD (standard HTML5 date input)
    - DD Mon YY: e.g., '06 Feb 26' (some mobile browsers)
    - DD Mon YYYY: e.g., '06 Feb 2026'
    - DD/MM/YYYY: e.g., '06/02/2026'
    - DD-MM-YYYY: e.g., '06-02-2026'
    - MM/DD/YYYY: e.g., '02/06/2026'
    """
    if not date_string:
        return None
    
    date_string = date_string.strip()
    
    # Try ISO format first (most common from HTML5 date inputs)
    try:
        return date.fromisoformat(date_string)
    except ValueError:
        pass
    
    # Try various other formats
    formats = [
        '%d %b %y',    # 06 Feb 26
        '%d %b %Y',    # 06 Feb 2026
        '%d/%m/%Y',    # 06/02/2026
        '%d/%m/%y',    # 06/02/26
        '%d-%m-%Y',    # 06-02-2026
        '%d-%m-%y',    # 06-02-26
        '%m/%d/%Y',    # 02/06/2026
        '%m/%d/%y',    # 02/06/26
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(
        f"Could not parse date: '{date_string}'. "
        f"Expected formats: YYYY-MM-DD, DD Mon YY, DD/MM/YYYY"
    )
