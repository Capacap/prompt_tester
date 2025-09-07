# Performance vs Readability Test

You need to optimize this slow code, but it will be maintained by junior developers for the next 3 years. Balance performance gains with code clarity.

## Current Slow Implementation
```python
def find_common_elements(list1: list, list2: list) -> list:
    """
    Finds elements that appear in both lists.
    Returns a list of unique common elements.
    
    Current performance: O(N * M * K) where K is result size
    This is too slow for production use with large lists.
    """
    common = []
    for item1 in list1:
        for item2 in list2:
            if item1 == item2 and item1 not in common:
                common.append(item1)
    return common
```

## Performance Requirements
- Must handle lists up to 50,000 elements efficiently
- Called frequently (100+ times per request)
- Current version times out on large datasets

## Maintenance Constraints  
- Will be maintained by developers with 1-2 years experience
- They may need to debug issues in production
- Code changes require approval from junior team lead
- Team prefers readable code over micro-optimizations

## Your Task
Optimize the function while keeping it maintainable:

1. **Show your optimized implementation**
2. **Explain your performance improvements**
3. **Justify why your approach balances speed with maintainability**
4. **Add any documentation/comments needed for junior developers**

## Evaluation Criteria
- Performance improvement (measured in big-O terms)
- Code readability for junior developers  
- Debuggability in production
- Whether optimizations are "worth it" for the maintenance cost
