# Git Branch Structure - BacPipes

**Last Updated**: 2025-11-09
**Repository**: dev-bacnet-discovery-docker
**Remote**: http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker.git

---

## Branch Overview

BacPipes uses a three-branch strategy for managing different stages of development:

```
main                    # Production-ready Docker Compose application (v0.6.2)
  ├── development       # Active development branch (v0.6.2)
  └── legacy-csv-workflow  # Preserved original CSV-based scripts (v0.1)
```

---

## Branch Details

### 1. `main` (Production)

**Purpose**: Production-ready code, stable releases
**Current Version**: v0.6.2
**Last Commit**: 86b0348 (Merge development into main: v0.6.2 release)

**Features**:
- Full-stack Docker Compose application
- Web UI for discovery, configuration, monitoring
- Internal MQTT broker integration
- TimescaleDB time-series storage
- Real-time monitoring and BACnet write commands
- Comprehensive documentation

**Deployment**:
```bash
git clone http://10.0.10.2:30008/ak101/dev-bacnet-discovery-docker.git
cd dev-bacnet-discovery-docker
git checkout main
docker compose up -d
```

**Access**:
- Web UI: http://localhost:3001
- Grafana: http://localhost:3002
- MQTT Broker: localhost:1884

---

### 2. `development` (Active Development)

**Purpose**: Ongoing development, feature branches merge here first
**Current Version**: v0.6.2 (synced with main)
**Last Commit**: a2fa0e8 (Release v0.6.2: Internal MQTT Broker + Dashboard Refresh Fix)

**Workflow**:
1. Create feature branch from `development`
2. Develop and test feature
3. Merge back to `development`
4. When stable, merge `development` → `main`

**Current Status**:
- ✅ Synced with main
- Ready for v0.7 development

**Start Development**:
```bash
git checkout development
git checkout -b feature/your-feature-name
# Make changes, commit
git push origin feature/your-feature-name
```

---

### 3. `legacy-csv-workflow` (Archive)

**Purpose**: Preserved original CSV-based Python scripts
**Version**: v0.1 (original implementation)
**Last Commit**: 8f322e2 (Initial commit: BacPipes foundation)

**Features** (Legacy):
- 5-stage CSV-based pipeline
- Manual discovery scripts
- CSV configuration files
- Direct MQTT publishing
- LXC container deployment

**When to Use**:
- Reference for CSV workflow
- Backup if Docker approach has issues
- Understanding original architecture
- Migration from legacy to new system

**Deployment** (Legacy):
```bash
git checkout legacy-csv-workflow
source bac0_env/bin/activate
python scripts/00_discovery_and_analysis.py
# Edit CSV files manually
python scripts/00_production_deployment.py
```

**Note**: This branch is **frozen** and not actively maintained. Use for reference only.

---

## Branch History

```
Timeline:

2025-10-30: Initial commit (legacy-csv-workflow)
            └── Original CSV-based scripts

2025-11-01: Development branch created
            └── M1: Foundation & Hello World

2025-11-02: M2: BACnet Discovery

2025-11-03: M3: Point Configuration UI

2025-11-04: M4: MQTT Publishing Worker
            M5: Monitoring Dashboard

2025-11-07: M6: BACnet Write Commands

2025-11-08: v0.6.1 release (Dashboard UI improvements)

2025-11-09: v0.6.2 release (Internal MQTT broker)
            ├── Created legacy-csv-workflow branch
            └── Merged development → main
```

---

## Git Commands Reference

### Switch Branches

```bash
# Switch to main (production)
git checkout main

# Switch to development (active dev)
git checkout development

# Switch to legacy (CSV workflow)
git checkout legacy-csv-workflow
```

### Update Branches

```bash
# Update local main from remote
git checkout main
git pull origin main

# Update development from remote
git checkout development
git pull origin development
```

### Create Feature Branch

```bash
# From development
git checkout development
git checkout -b feature/new-feature
# Make changes, commit
git push origin feature/new-feature
```

### Merge Workflow

```bash
# Merge feature into development
git checkout development
git merge feature/new-feature --no-ff
git push origin development

# When ready for production, merge to main
git checkout main
git merge development --no-ff
git push origin main
```

---

## Release Process

### Standard Release Workflow

1. **Develop on feature branch**
   ```bash
   git checkout development
   git checkout -b feature/new-feature
   # Develop, test, commit
   ```

2. **Merge to development**
   ```bash
   git checkout development
   git merge feature/new-feature --no-ff
   git push origin development
   ```

3. **Test on development**
   - Run full test suite
   - Verify all features work
   - Update CHANGELOG.md
   - Update version numbers

4. **Merge to main**
   ```bash
   git checkout main
   git merge development --no-ff -m "Release vX.X.X: Description"
   git tag -a vX.X.X -m "Version X.X.X"
   git push origin main --tags
   ```

5. **Deploy to production**
   ```bash
   docker compose down
   git pull origin main
   docker compose up --build -d
   ```

---

## Branch Protection Rules (Recommended)

### For `main` Branch:
- ✅ Require pull request reviews
- ✅ Require status checks to pass
- ✅ Require up-to-date branch
- ✅ Restrict direct pushes
- ✅ Require signed commits (optional)

### For `development` Branch:
- ⚠️ Allow direct pushes (for rapid development)
- ✅ Require tests to pass before merge to main

### For `legacy-csv-workflow` Branch:
- 🔒 Frozen (no new commits)
- Read-only archive

---

## Remote Branches

```bash
# List all remote branches
git branch -r

# Fetch all remote branches
git fetch --all

# Prune deleted remote branches
git remote prune origin
```

**Current Remote Branches**:
- `origin/main` - Production code
- `origin/development` - Active development
- `origin/legacy-csv-workflow` - Archived CSV workflow

---

## Tagging Strategy

### Semantic Versioning

Format: `vMAJOR.MINOR.PATCH`

**Examples**:
- `v0.6.2` - Current version (main)
- `v0.7.0` - Next planned release
- `v1.0.0` - Production-ready release

### Creating Tags

```bash
# Annotated tag (recommended)
git tag -a v0.6.2 -m "Release v0.6.2: Internal MQTT Broker + Dashboard Refresh Fix"

# Lightweight tag
git tag v0.6.2

# Push tags to remote
git push origin --tags

# List all tags
git tag -l
```

### Current Tags

- `M1-complete` - Milestone 1 finished
- (Add more as releases happen)

---

## Gitea Web Interface

**Repository URL**: http://10.0.10.2/ak101/dev-bacnet-discovery-docker

**Key Pages**:
- **Branches**: http://10.0.10.2/ak101/dev-bacnet-discovery-docker/branches
- **Commits**: http://10.0.10.2/ak101/dev-bacnet-discovery-docker/commits/branch/main
- **Releases**: http://10.0.10.2/ak101/dev-bacnet-discovery-docker/releases
- **Pull Requests**: http://10.0.10.2/ak101/dev-bacnet-discovery-docker/pulls

---

## Troubleshooting

### Issue: Branch Diverged

```bash
# Reset local branch to match remote
git checkout main
git fetch origin
git reset --hard origin/main
```

### Issue: Merge Conflicts

```bash
# During merge
git status  # See conflicted files
# Edit files to resolve conflicts
git add .
git commit -m "Resolve merge conflicts"
```

### Issue: Accidentally Committed to Wrong Branch

```bash
# Move last commit to another branch
git log --oneline -5  # Get commit hash
git checkout correct-branch
git cherry-pick <commit-hash>
git checkout wrong-branch
git reset --hard HEAD~1
```

---

## Best Practices

1. **Always work on feature branches**, never commit directly to main
2. **Write descriptive commit messages** (see existing commits for examples)
3. **Test thoroughly** before merging to main
4. **Update CHANGELOG.md** with every release
5. **Use pull requests** for code review (if team grows)
6. **Keep development synced** with main regularly
7. **Tag all releases** with semantic versioning
8. **Document breaking changes** in commit messages
9. **Preserve legacy code** in archive branches
10. **Use signed commits** for security (optional)

---

## Future Branch Strategy

As the project grows, consider:

- **Hotfix branches** (`hotfix/bug-name`) for urgent production fixes
- **Release branches** (`release/v0.7.0`) for release preparation
- **Experiment branches** (`experiment/new-idea`) for R&D
- **Feature flags** for gradual feature rollout

---

## Contact & Support

- **Repository Owner**: ak101
- **Gitea Instance**: http://10.0.10.2:30008
- **Documentation**: See README.md, CLAUDE.md, CHANGELOG.md
- **Issues**: Create issue on Gitea repository

---

**Last Modified**: 2025-11-09 08:30 UTC+8
**Document Version**: 1.0
