# AI Documentation Generation Agency - Agents & Tools Overview

## Documentation Agent
Responsible for analyzing repositories and generating documentation according to standards.

### Tools
1. **RepositoryAnalyzer**
   - Detects repository type and patterns
   - Analyzes codebase structure
   - Extracts metadata and language information
   - Maps repo structure to documentation requirements

2. **StandardSelector**
   - Selects appropriate documentation standards
   - Loads and validates templates
   - Configures documentation rules
   - Matches standards to repository type

3. **ContentGenerator**
   - Generates documentation content
   - Applies templates and standards
   - Handles different repository types
   - Creates consistent documentation structure

4. **TemplateManager**
   - Manages documentation templates
   - Applies template variables
   - Validates template requirements
   - Ensures consistency across docs

5. **FeedbackProcessor** (New)
   - Parses structured feedback from Review Agent
   - Prioritizes revisions
   - Tracks changes made
   - Validates improvements

6. **ContentReviser** (New)
   - Applies specific feedback
   - Maintains document consistency
   - Tracks revision history
   - Ensures no regressions

## GitHub Agent
Handles all GitHub repository interactions and management.

### Tools
1. **RepositoryManager** (Exists)
   - Manages repository cloning
   - Handles repository configuration
   - Controls repository access
   - Manages local repository state

2. **PullRequestManager** (Exists)
   - Creates and updates pull requests
      - PR title: 'docs: Update documentation year-month-day-hour'
   - Manages PR lifecycle
   - Handles PR validation
   - Tracks PR status

3. **CommentManager** (Exists)
   - Creates and manages comments
   - Handles review comments
   - Manages comment threads
   - Coordinates review discussions

4. **BranchManager** (Needed)
   - Creates branches for documentation generation
   - branchs naming pattern: docs/<repo-name>/<year-month-day-hour>


## Review Agent
Ensures documentation quality through review and feedback.

### Tools
1. **QualityAnalyzer**
   - Assesses documentation quality
   - Calculates quality metrics
   - Generates quality reports
   - Tracks quality trends over iterations

2. **TechnicalValidator**
   - Validates technical accuracy using LLM
   - Checks code examples using LLM
   - Verifies documentation completeness using LLM
   - Validates against repository requirements using LLM

3. **FeedbackGenerator**
   - Generates structured feedback using LLM
   - Prioritizes issues using LLM
   - Suggests improvements using LLM
   - Creates actionable recommendations using LLM

4. **ReviewCoordinator**
   - Manages review iterations
   - Tracks feedback resolution using LLM
   - Coordinates review cycles
   - Handles review session state

## Tool Integration Requirements
- All tools must integrate with event bus
- Tools must support rate limiting
- Tools must implement proper error handling
- Tools must include logging and monitoring
- Tools should use cache when appropriate
- Tools must support async operations

## Quality Thresholds
```python
QUALITY_THRESHOLDS = {
    'readability': 0.8,
    'technical_accuracy': 0.9,
    'completeness': 0.85,
    'example_quality': 0.85
}

REVIEW_LIMITS = {
    'max_iterations': 5,
    'timeout_minutes': 30,
    'min_improvement': 0.05
}
```

## Event Types
```python
DOCUMENTATION_EVENTS = {
    'SUBMITTED': 'documentation.submitted',
    'REVISION_STARTED': 'documentation.revision_started',
    'REVISION_COMPLETE': 'documentation.revision_complete'
}

REVIEW_EVENTS = {
    'FEEDBACK_GENERATED': 'review.feedback_generated',
    'QUALITY_UPDATE': 'review.quality_threshold',
    'APPROVED': 'review.approved',
    'REJECTED': 'review.rejected'
}
```

## Repository Types Supported
1. **Spring Boot Backends**
   - Focus on application properties
   - Java source documentation
   - REST API documentation

2. **NGINX Frontends**
   - NGINX configuration docs
   - Web server setup guides
   - Deployment documentation

3. **Bounded Context**
   - Helm chart documentation
   - Terraform module docs
   - Infrastructure diagrams

4. **Unknown Repositories**
   - Generic documentation
   - Flexible structure
   - Adaptable templates

5. **Python Repositories**
   - Python module docs
   - Package requirements
   - Setup instructions

All tools follow a common interface pattern and integrate with the agency's core services for event management, caching, rate limiting, and logging.