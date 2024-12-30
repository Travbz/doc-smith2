# Event Bus Service

The event bus enables asynchronous communication between agents, helping coordinate the documentation generation workflow. Think of it as a central nervous system - agents publish events about their work, and interested agents can subscribe to learn about and react to those events.

## Key Concepts

### Messages Flow Like This:
1. Documentation Agent analyzes a repo and generates docs
2. It publishes a "docs ready" event
3. Review Agent subscribes to this event
4. Review Agent automatically starts reviewing when docs arrive
5. When review is done, it publishes feedback
6. Documentation Agent sees feedback and improves the docs

### It's Helpful Because:
- Agents work independently but stay coordinated 
- Work happens automatically - one action triggers the next
- Everyone can react to events they care about
- Easy to add new behaviors by subscribing to existing events

## Core Events

### Documentation Events
When documentation gets created or updated:
- documentation.submitted: New docs ready for review
- documentation.revised: Changes made based on feedback
- documentation.completed: Final docs approved and ready

### Review Events  
When docs are being checked:
- review.started: Beginning review of docs
- review.feedback: Found things to improve
- review.approved: Docs look good to go

### GitHub Events
When working with the repository:
- github.pr_created: New docs PR opened
- github.pr_updated: Made changes to PR
- github.pr_merged: Docs merged into main branch

## Adding New Features

Want to add something new? Here's the pattern:

1. Look at existing events to react to
2. Subscribe your code to relevant events
3. Handle the events when they arrive
4. Publish your own events others might want

For example, adding automated spell check:
```python
# Subscribe to new docs
@event_bus.subscribe("documentation.submitted")
async def check_spelling(data):
    # Run spell check
    issues = spell_checker.check(data.content)
    
    # Report any problems
    if issues:
        await event_bus.publish("review.feedback", {
            "type": "spelling",
            "issues": issues
        })
```

### When should I publish events?
When you've done something others might want to know about or react to. Examples:
- Finished generating docs
- Found issues in review
- Created or updated a PR

### What should I subscribe to?
Think about what needs to trigger your code. Common patterns:
- Review Agent watches for new docs
- Documentation Agent watches for feedback
- GitHub Agent watches for approved docs

### How do I handle failures?
The event bus handles retries and error recovery. Focus on:
1. Proper error handling in your code
2. Idempotent event handlers (safe to run multiple times)
3. Publishing events when you need to signal problems