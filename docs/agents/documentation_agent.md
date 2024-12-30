# Documentation Agent

The Documentation Agent analyzes repositories and generates documentation, working closely with Review and GitHub agents to ensure quality and integration.

## Repository Analysis
- Uses file patterns to detect repository type:
  ```python
  REPO_PATTERNS = {
    "spring_boot": ["pom.xml", "application.properties"],
    "nginx": ["nginx.conf", "sites-enabled"],
    "bounded_context": ["helm/", "terraform/"],
    "python": ["setup.py", "requirements.txt"]
  }
  ```
- Maps repository structure for documentation generation

## Documentation Generation
- Selects appropriate documentation standard based on repository type
- Generates repository-specific documentation:
  - Spring Boot: API docs, service architecture
  - NGINX: Server config, deployment docs  
  - Bounded Context: Infrastructure, deployment flows
  - Python: Module docs, setup guides
  - Unknown: Generic documentation with detected patterns

## Interactions

### Review Agent
- Submits generated docs for review via event bus
- Receives structured feedback with quality scores
- Updates documentation based on feedback:
  ```json
  {
    "feedback": {
      "technical_accuracy": 0.85,
      "completeness": 0.90,
      "required_changes": [
        {
          "file": "README.md",
          "section": "Setup",
          "suggestion": "Add environment configuration"
        }
      ]
    }
  }
  ```

### GitHub Agent  
- Receives repository content via clone operation
- Submits documentation changes via pull requests
- Tracks PR status and review comments