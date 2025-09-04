I'm building a notification system that needs to send messages via email, SMS, and push notifications. The system should be easily extensible for new notification types. What design patterns would you recommend?

Current requirements:
- Multiple notification channels (email, SMS, push)
- Different message formats for each channel
- Easy to add new channels without modifying existing code
- Support for notification preferences per user
- Ability to retry failed notifications
- Logging and monitoring of delivery status
