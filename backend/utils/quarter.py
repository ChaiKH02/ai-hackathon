from datetime import datetime

def get_quarter(date_str):
    """
    Convert a date string in D/M/Y format to its corresponding quarter.
    
    Args:
        date_str (str): Date string in "YYYY-MM-DD" format (e.g., "2024-03-15")
    
    Returns:
        str: Quarter in format "Q1", "Q2", "Q3", or "Q4"
    
    Raises:
        ValueError: If the date string is invalid or not in the correct format
    
    Examples:
        >>> get_quarter("2024-03-15")
        'Q1'
        >>> get_quarter("2024-07-01")
        'Q3'
    """
    try:
        # Parse the date string in D/M/Y format
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Get the month (1-12)
        month = date_obj.month
        
        # Calculate quarter based on month
        if month <= 3:
            return "Q1"
        elif month <= 6:
            return "Q2"
        elif month <= 9:
            return "Q3"
        else:
            return "Q4"
    except ValueError as e:
        raise ValueError(f"Invalid date format. Expected 'YYYY-MM-DD' format (e.g., '2024-03-15'). Error: {str(e)}")