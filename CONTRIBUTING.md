# Contributing to RAG Document System

Thank you for your interest in contributing! This guide explains our development workflow and branch protection rules.

---

## 📋 Quick Start

### 1. Clone and Setup
```bash
git clone https://github.com/Darshan-302/rag-doc-system.git
cd rag-doc-system
git checkout development
```

### 2. Create Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes
```bash
# Edit files, test locally
git add .
git commit -m "feat: description of your change"
```

### 4. Push to Remote
```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request
- Go to: https://github.com/Darshan-302/rag-doc-system/pulls
- Click **"New Pull Request"**
- **Base branch: `development`** (NOT main!)
- Add clear title and description
- Request review from `@Darshan-302`

### 6. Address Feedback
```bash
# Make requested changes
git add .
git commit -m "refactor: address review feedback"
git push origin feature/your-feature-name
# PR updates automatically
```

### 7. Merge
Wait for `@Darshan-302` approval and merge. Branch will be deleted automatically.

---

## 🌳 Branch Structure

### Public Branches (Protected)
These branches are protected and require code review:

- **`main`** - Production code
  - Only merged to via release PRs
  - Tagged with version numbers
  - Used for deployments
  
- **`development`** - Staging/development
  - Main integration branch
  - All feature PRs merge here first
  - Tested before release
  
- **`release/*`** - Release branches
  - Created from development when releasing
  - Example: `release/v1.0.0`
  - Merged to main for production

### Developer Branches (Unprotected)
You can freely work on these:

- **`feature/*`** - New features
  - Example: `feature/user-authentication`
  - Create from: `development`
  - Merge to: `development`
  
- **`bugfix/*`** - Bug fixes
  - Example: `bugfix/login-error`
  - Create from: `development`
  - Merge to: `development`
  
- **`hotfix/*`** - Emergency fixes
  - Example: `hotfix/security-patch`
  - Create from: `main`
  - Merge to: `main` AND `development`
  
- **`task/*`** - Tasks/refactoring
  - Example: `task/code-cleanup`
  - Create from: `development`
  - Merge to: `development`
  
- **`chore/*`** - Chores (deps, etc.)
  - Example: `chore/update-dependencies`
  - Create from: `development`
  - Merge to: `development`

---

## 🔐 Branch Protection Rules

### Protected Branches Require
✅ **Pull request review** (1 approval needed)
✅ **Passing status checks** (if configured)
✅ **Up-to-date with base branch** before merging
✅ **Linear history** (no merge commits)

### What's Blocked
❌ Direct pushes (except owner)
❌ Force pushes (except owner)
❌ Deletions (except owner)
❌ Merging without approval

### Owner Capabilities
✅ Can force push if needed (emergency only)
✅ Can approve and merge PRs
✅ Can change branch protection rules
✅ Can delete branches
✅ Can override protections if necessary

---

## 💻 Development Workflow

### Basic Flow
```
development (latest stable)
    ↓
    └─→ feature/my-feature (your work)
        ├─ Commit 1: Add feature
        ├─ Commit 2: Add tests
        └─ Commit 3: Fix review feedback
            ↓
        └─→ Create PR → development
            └─→ Review by @Darshan-302
                ├─ Approved: Merge
                └─ Changes requested: Update & push again
```

### Multiple Features
```
You can work on multiple features in parallel:

git checkout development
git checkout -b feature/feature-1
# ... work on feature-1 ...
git push origin feature/feature-1
# Create PR for feature-1

git checkout development
git checkout -b feature/feature-2
# ... work on feature-2 ...
git push origin feature/feature-2
# Create PR for feature-2
# Now you have 2 PRs pending review
```

### Release Flow
```
1. When ready to release from development:
   git checkout development
   git pull origin development
   git checkout -b release/v1.0.0

2. Make release changes (version bump, changelog, etc.)
   git push origin release/v1.0.0

3. Create PR: release/v1.0.0 → main
   - Get approval
   - Merge to main

4. Tag the release:
   git checkout main
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0

5. Merge main back to development:
   git checkout development
   git pull origin main
   git push origin development
```

---

## 📝 Commit Messages

Follow conventional commits:

### Format
```
<type>: <description>

<optional body>
<optional footer>
```

### Types
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `test:` - Tests
- `docs:` - Documentation
- `chore:` - Dependencies, tooling
- `style:` - Formatting
- `perf:` - Performance improvement

### Examples
```bash
git commit -m "feat: add user authentication"
git commit -m "fix: resolve login redirect issue"
git commit -m "refactor: simplify RAG pipeline"
git commit -m "docs: update README with setup instructions"
git commit -m "chore: update dependencies"
```

---

## 🧪 Before Creating a PR

### 1. Code Quality
```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

### 2. Tests
```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v
```

### 3. Local Testing
```bash
# Start services
docker-compose up -d

# Run application
python -m uvicorn src.main:app --reload

# Test API
curl -X POST "http://localhost:8000/api/v1/default-tenant/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "top_k": 5}'
```

### 4. Commit and Push
```bash
git add .
git commit -m "feat: clear description"
git push origin feature/your-feature
```

---

## 📋 PR Description Template

When creating a PR, use this template:

```markdown
## Description
Brief description of what changed and why.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Closes #123 (if applicable)

## Testing Done
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] No new warnings

## Screenshots
(if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Tests updated/added
- [ ] Documentation updated
```

---

## 🔄 Code Review Process

### What Gets Reviewed
- Code correctness
- Security implications
- Performance impact
- Test coverage
- Documentation
- Compliance with standards

### Review Feedback
- ✅ Approved: Ready to merge
- 📝 Changes requested: Make updates and push again
- 💬 Comments: Acknowledge and respond

### Addressing Feedback
```bash
# Make requested changes
vim src/file.py

# Commit and push
git add .
git commit -m "refactor: address review feedback"
git push origin feature/your-feature

# PR automatically updates
# No need to close and recreate
```

---

## ❌ Common Mistakes

### ❌ Wrong Base Branch
```bash
# DON'T: Create PR with base: main
# DO: Create PR with base: development
```

### ❌ Force Push After PR Created
```bash
# DON'T:
git push -f origin feature/my-feature

# DO: Make a normal commit
git commit -m "fix: address feedback"
git push origin feature/my-feature
```

### ❌ Direct Push to Protected Branch
```bash
# DON'T:
git push origin development  # Will be rejected!

# DO: Create PR and wait for approval
```

### ❌ Merging Your Own PR
```bash
# Only @Darshan-302 can merge
# You cannot merge your own PR
```

---

## 🆘 Troubleshooting

### "Permission denied" on push
```bash
# You're trying to push to a protected branch
# Solution: Push to your feature branch instead
git push origin feature/my-feature
```

### "Rejected: Your branch is behind"
```bash
# development has new commits
# Solution: Update your branch
git fetch origin
git rebase origin/development
git push -f origin feature/my-feature  # OK to force push on feature branch
```

### "Failed to create pull request"
```bash
# Make sure:
# 1. Feature branch is pushed
# 2. Branch name is correct
# 3. You have permission to create PRs
```

### Cannot merge PR
```bash
# Only @Darshan-302 can merge
# Wait for owner to review and merge
```

---

## 📚 Additional Resources

- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Branch Naming Conventions](./docs/BRANCH_NAMING.md)
- [Code Style Guide](./docs/CODE_STYLE.md)

---

## ❓ Questions?

If you have questions:
1. Check existing issues
2. Create a new issue with your question
3. Contact `@Darshan-302`

---

## ✅ Checklist Before Submitting PR

- [ ] Branch created from `development`
- [ ] Changes are focused and small
- [ ] Code passes linting and type checks
- [ ] Tests written/updated
- [ ] All tests pass locally
- [ ] PR description is clear
- [ ] Base branch is `development`
- [ ] No merge conflicts
- [ ] Ready for review

---

**Thank you for contributing! 🚀**
