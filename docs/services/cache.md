# Cache Service

The cache service speeds up repeated operations by storing recently generated content. Think of it like a whiteboard where we write down answers - if someone asks the same question again, we can just look at the whiteboard instead of recalculating everything.

## What Gets Cached?

### Repository Analysis Results 
- File structure maps
- Detected repository types
- Key component locations
Saves time when working with the same repository multiple times.

### Documentation Standards
- Templates 
- Style guides
- Required sections
Frequently used standards stay readily available.

### Quality Metrics
- Analysis results
- Review scores
- Feedback patterns 
Helps track improvement across revisions.

## How Long Things Stay Cached

### Short Term (1 hour)
- Quality check results
- Validation outputs
- Review feedback
Things that might change as docs improve.

### Medium Term (24 hours)  
- Repository analysis
- Documentation standards
- Generated templates
More stable information.

### Until Changed
- Approved documentation versions
- Final review decisions
- Merged PR statuses
Important historical records.

## Common Uses

### Documentation Agent
Uses cache to:
- Remember repository structures
- Keep track of chosen standards
- Store partially generated docs

### Review Agent  
Uses cache to:
- Track review progress
- Compare quality over time
- Remember previous feedback

### GitHub Agent
Uses cache to:
- Track PR statuses
- Store repository metadata
- Remember branch states

## Best Practices

### When to Cache
- Expensive calculations
- Frequently accessed data
- Results that rarely change

### When Not to Cache
- Rapidly changing data
- Sensitive information
- Large binary content

### Cache Maintenance
- Items expire automatically
- Old entries get cleaned up
- Cache clears on service restart