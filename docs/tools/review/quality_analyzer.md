# Quality Analyzer Tool

## Analysis Flow
1. Receives documentation from Review Agent
2. Runs quality checks:
   - Technical accuracy
   - Content completeness
   - Code example validation
3. Generates quality metrics
4. Provides feedback

## Quality Metrics
```python
METRICS = {
    'technical': {
        'code_correctness': 0.4,
        'api_accuracy': 0.3,
        'config_validity': 0.3
    },
    'content': {
        'completeness': 0.4,
        'clarity': 0.3,
        'organization': 0.3
    },
    'examples': {
        'correctness': 0.4,
        'coverage': 0.3,
        'clarity': 0.3
    }
}

THRESHOLDS = {
    'technical': 0.9,
    'content': 0.85,
    'examples': 0.85
}
```

## Integration Points
- Review Agent: Receives docs, returns quality assessment
- Documentation Agent: Feedback for improvements
- FeedbackGenerator: Quality metrics for feedback

## Quality Report
```json
{
  "quality_score": 0.87,
  "sections": {
    "technical": {
      "score": 0.92,
      "issues": []
    },
    "content": {
      "score": 0.84,
      "issues": [
        {
          "type": "missing_section",
          "section": "Troubleshooting",
          "severity": "medium"
        }
      ]
    }
  }
}
```