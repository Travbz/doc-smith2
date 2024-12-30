# Review Agent

Validates documentation quality through automated analysis and coordinates review cycles.

## Quality Analysis
- Checks technical accuracy:
  ```python
  QUALITY_THRESHOLDS = {
    'technical_accuracy': 0.9,  # Code, APIs, configs
    'completeness': 0.85,      # Required sections
    'readability': 0.8         # Clarity, structure
  }
  ```
  
## Review Process 
1. Receives documentation via `documentation.submitted`
2. Runs quality analysis and technical validation
3. Generates structured feedback for Documentation Agent
4. Tracks improvements across iterations

## Interactions

### Documentation Agent
- Processes submitted documentation
- Provides feedback via `review.feedback_generated`
- Approves or rejects documentation:
  ```json
  {
    "status": "rejected",
    "reasons": [
      {
        "type": "missing_content",
        "severity": "high",
        "details": "API authentication docs required"
      }
    ]
  }
  ```

### GitHub Agent
- Reviews pull request content
- Adds review comments to PRs
- Approves PRs on passing validation