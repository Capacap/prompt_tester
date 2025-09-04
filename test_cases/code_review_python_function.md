Please review this Python function for potential issues:

```python
def calculate_total(items):
    total = 0
    for item in items:
        if item['price'] > 0:
            total += item['price']
    return total
```
