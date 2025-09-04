This code works but feels messy. How would you refactor it to be more maintainable?

```python
def process_user_data(user_data):
    if user_data is None:
        return None
    
    result = {}
    
    if 'name' in user_data and user_data['name'] is not None:
        if len(user_data['name'].strip()) > 0:
            result['name'] = user_data['name'].strip().title()
        else:
            result['name'] = 'Unknown'
    else:
        result['name'] = 'Unknown'
    
    if 'email' in user_data and user_data['email'] is not None:
        email = user_data['email'].strip().lower()
        if '@' in email and '.' in email:
            result['email'] = email
        else:
            result['email'] = None
    else:
        result['email'] = None
    
    if 'age' in user_data:
        try:
            age = int(user_data['age'])
            if age >= 0 and age <= 150:
                result['age'] = age
            else:
                result['age'] = None
        except:
            result['age'] = None
    else:
        result['age'] = None
    
    return result
```
