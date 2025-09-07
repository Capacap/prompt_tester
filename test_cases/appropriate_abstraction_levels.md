# Appropriate Abstraction Level Test

You're given three scenarios with different complexity levels. For each, choose the appropriate level of abstraction and justify your decision.

## Scenario A: Simple Utility
**Task**: Calculate the average of a list of numbers, handling edge cases.

**Requirements**:
- Handle empty lists (return 0 or raise exception?)
- Handle non-numeric values
- Used in 3-4 places in the codebase
- Team size: 2 developers

**Question**: What level of abstraction is appropriate? Show your implementation.

## Scenario B: User Registration System  
**Task**: Process user registration with validation, email sending, and database storage.

**Requirements**:
- Validate email, password strength, username availability
- Send welcome email and email verification
- Store user in database with proper error handling
- Log registration events for analytics
- Used across web app, mobile API, and admin interface
- Team size: 8 developers
- System handles 1000+ registrations/day

**Question**: How do you structure this code? Show your key abstractions and interfaces.

## Scenario C: Enterprise SaaS Billing  
**Task**: Multi-tenant billing system with complex pricing rules.

**Requirements**:
- Support multiple pricing models (per-user, usage-based, tiered)
- Handle pro-rations, discounts, taxes by region
- Generate invoices, process payments, handle failures
- Audit trails, compliance reporting
- Integration with multiple payment processors
- Team size: 25 developers across 3 teams
- System processes millions in revenue

**Question**: What architectural patterns and abstractions would you use? Show the high-level structure.

## Evaluation Criteria
For each scenario, justify:
1. **Why your chosen abstraction level fits the problem complexity**
2. **How it scales with team size and usage**  
3. **What you specifically avoided over-engineering or under-engineering**
4. **How the design supports future changes**
