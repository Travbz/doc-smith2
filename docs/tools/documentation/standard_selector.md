# Standard Selector Tool

## Standard Selection Flow
1. Receives repository analysis results
2. Loads standards from YAML configs
3. Matches repo type to standard
4. Configures templates and rules

## Standards Configuration
```yaml
spring_boot:
  required_sections:
    - API Documentation
    - Authentication
    - Service Architecture
    - Database Schema
  templates:
    - api_docs.md
    - service_arch.md
    
python:
  required_sections:
    - Installation
    - Module Documentation
    - API Reference
  templates:
    - module_docs.md
    - setup_guide.md
```

## Integration Points
- RepositoryAnalyzer: Receives repo type
- ContentGenerator: Provides selected standards
- TemplateManager: Configures templates

## Validation Rules
```python
VALIDATION_RULES = {
    "api_docs": {
        "required": ["endpoints", "auth", "params"],
        "optional": ["examples", "errors"]
    },
    "setup": {
        "required": ["prerequisites", "installation"],
        "optional": ["troubleshooting"]
    }
}
```