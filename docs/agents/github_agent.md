# GitHub Agent 

Manages repository operations and documentation integration through GitHub's API.

## Core Operations
- Clones repositories for Documentation Agent
- Creates documentation branches:
  ```shell
  docs/<repo-name>/<timestamp>
  ```
- Submits pull requests with generated docs
- Manages review comments and iterations

## Documentation Integration
- Branch naming: `docs/update-YYYY-MM-DD-HH`
- PR title format: `docs: update documentation YYYY-MM-DD`
- Commit message standards:
  ```
  docs: <scope> updates
  
  - Add API documentation
  - Update deployment guide
  - Fix configuration examples
  ```

## Interactions

### Documentation Agent
- Provides repository access
- Creates PRs with generated content
- Tracks documentation updates

### Review Agent
- Processes review comments
- Updates PRs based on feedback
- Merges approved documentation

## Review Flow
1. Create documentation branch
2. Push generated content
3. Open pull request
4. Process review feedback
5. Merge on approval