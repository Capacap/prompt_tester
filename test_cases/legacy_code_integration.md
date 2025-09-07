# Legacy Code Integration Test

You need to add a new feature to this existing codebase. The current system has been working in production for 2 years.

## Existing System
```python
# Existing order management system
def get_user_orders(user_id: str) -> list:
    """Returns list of order dictionaries for a user"""
    # Implementation details hidden - assume this works
    pass

def calculate_shipping(order: dict) -> float:
    """Calculates shipping cost based on order weight and destination"""
    # Implementation details hidden - assume this works  
    pass

def get_user_tier(user_id: str) -> str:
    """Returns user tier: 'bronze', 'silver', 'gold', 'platinum'"""
    # Implementation details hidden - assume this works
    pass
```

## New Requirement
Add a function to calculate the total order value including:
- Base order total (from order['total'])
- Shipping costs 
- Tax rate of 8.5%
- Discount based on user tier:
  - Bronze: 0% discount
  - Silver: 5% discount  
  - Gold: 10% discount
  - Platinum: 15% discount

## Focus Areas
Your solution should:
1. Integrate cleanly with the existing codebase style
2. Be easy for the current team to understand and maintain
3. Handle edge cases appropriately
4. Follow the same patterns as existing code

Write the function and explain your design choices.
