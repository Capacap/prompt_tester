I'm experiencing memory leaks in this Python class. Can you help identify the issue?

```python
class DataProcessor:
    def __init__(self):
        self.cache = {}
        self.callbacks = []
    
    def process_data(self, data, callback):
        # Cache the processed data
        processed = self._expensive_operation(data)
        self.cache[id(data)] = processed
        
        # Store callback for later use
        self.callbacks.append(callback)
        
        return processed
    
    def _expensive_operation(self, data):
        # Simulate expensive computation
        return [x * 2 for x in data]
```
