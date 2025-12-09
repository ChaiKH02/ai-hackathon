import holidays
from datetime import datetime, timedelta

def classify_festival_date(input_date, year=2026):
    """
    Classify a date as pre-festival, festival, post-festival, or normal day
    based on Malaysian public holidays.
    
    Args:
        input_date: Can be a datetime object or string in format 'YYYY-MM-DD'
        year: Year for holidays (default: 2026)
    
    Returns:
        list: List of classifications for the date (can have multiple if near multiple festivals)
    """
    # Convert string to datetime if needed
    if isinstance(input_date, str):
        input_date = datetime.strptime(input_date, '%Y-%m-%d')
    
    # Get Malaysian holidays for the specified year
    my_holidays = holidays.MY(years=year)
    
    results = []
    
    # Check all holidays in the year
    for holiday_date, holiday_name in my_holidays.items():
        # Convert holiday_date to datetime for comparison
        holiday_dt = datetime.combine(holiday_date, datetime.min.time())
        
        # Calculate difference in days
        days_diff = (input_date - holiday_dt).days
        
        # Classify based on difference
        if days_diff == 0:
            # Exact match - it's the festival day
            results.append(f"festival: {holiday_name}")
        elif -15 <= days_diff < 0:
            # 1-15 days before the festival
            results.append(f"pre-festival: {holiday_name}")
        elif 0 < days_diff <= 15:
            # 1-15 days after the festival
            results.append(f"post-festival: {holiday_name}")
    
    # If no results, it's a normal day
    if not results:
        results.append("normal day")
    
    return results


# # Example usage
# if __name__ == "__main__":
#     # Test with different dates
#     test_dates = [
#         "01/01/2026",  # New Year's Day (festival)
#         "20/12/2026",  # Pre-Christmas
#         "15/01/2026",  # Post New Year
#         "15/03/2026",  # Normal day
#     ]
    
#     print("Malaysian Festival Date Classification\n" + "="*50)
    
#     for date_str in test_dates:
#         classifications = classify_festival_date(date_str)
#         print(f"\nDate: {date_str}")
#         for classification in classifications:
#             print(f"  - {classification}")
    