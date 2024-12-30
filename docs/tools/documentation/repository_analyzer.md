# Repository Analyzer Tool

## Workflow
1. Receives repository path from Documentation Agent
2. Analyzes file structure and patterns
3. Determines repository type and primary languages
4. Maps critical components for documentation

## Type Detection Logic
```python
def detect_repo_type(files: List[str]) -> str:
    if any(f.endswith(".py") for f in files):
        if "main.py" in files or "setup.py" in files:
            return "python"
            
    if "pom.xml" in files or "application.properties" in files:
        return "spring_boot"
        
    if "nginx.conf" in files:
        return "nginx"
        
    if "helm" in files or "terraform" in files:
        return "bounded_context"
        
    return "unknown"
```

## Outputs
```json
{
  "repo_type": "spring_boot",
  "languages": ["java", "xml"],
  "key_components": {
    "api": ["src/main/java/**/controller"],
    "config": ["src/main/resources"],
    "services": ["src/main/java/**/service"]
  }
}
```

## Integration Points
- Documentation Agent: Repository analysis results
- StandardSelector: Type-based standard selection
- ContentGenerator: Component mapping for docs