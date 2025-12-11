# Prisma Schema Migration Guide - December 2025

## Quick Start (Ubuntu 20 System)

**If you just pulled this code and want to deploy:**

```bash
# 1. Pull latest changes
git pull origin development

# 2. Start services (migration applies automatically)
docker compose up -d

# 3. Verify migration applied
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT migration_name FROM _prisma_migrations ORDER BY finished_at;
"
# Should show 2 migrations

# 4. Test the app
# Open browser: http://<your-ip>:3001
# Dashboard should load WITHOUT "System Error: Failed to fetch dashboard data"
```

---

## Problem Fixed

**Issue:** Fresh deployments failed with "System Error: Failed to fetch dashboard data"

**Root Cause:** 7 database columns existed in the database but were not tracked by Prisma migrations, causing schema drift.

**Missing Columns:**
- `dis` - Human-readable display name
- `quantity`, `subject`, `location`, `qualifier` - Haystack semantic tagging fields
- `minPresValue`, `maxPresValue` - Value range validation fields

**Solution:** Created migration `20251210172641_add_haystack_validation_fields` that adds these 7 columns using `IF NOT EXISTS` (idempotent).

---

## What Was Changed

**Commit:** `a6bf557`
**Date:** 2025-12-10
**Files Modified:**
1. ✅ `frontend/prisma/migrations/20251210172641_add_haystack_validation_fields/migration.sql` (NEW)
2. ✅ `frontend/src/app/points/page.tsx` - Removed unused `pointType` field
3. ✅ `frontend/src/components/PointEditor.tsx` - Removed unused `pointType` field

---

## Deployment Instructions (Ubuntu 20)

### Step 1: Pull and Start

```bash
cd /home/ak101/bacnet  # Or clone: git clone http://10.0.10.2:30008/ak101/app-bacnet-local.git

# Pull latest changes
git pull origin development

# Verify migration file exists
cat frontend/prisma/migrations/20251210172641_add_haystack_validation_fields/migration.sql

# Start services
docker compose up -d
```

**What happens automatically:**
- Frontend container detects new migration on startup
- Applies migration to database
- No manual commands needed!

---

### Step 2: Verification

Run these commands to verify everything works:

```bash
# 1. Check all services running
docker compose ps
# Expected: postgres, frontend, worker all "Up"

# 2. Check migration logs
docker logs bacpipes-frontend 2>&1 | grep -i "migration"
# Expected: "2 migrations found"

# 3. Verify both migrations in database
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT migration_name, finished_at
  FROM _prisma_migrations
  ORDER BY finished_at;
"
# Expected output:
# 20251101055716_init
# 20251210172641_add_haystack_validation_fields

# 4. Verify 7 columns exist
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'Point'
  AND column_name IN ('dis', 'quantity', 'subject', 'location', 'qualifier', 'minPresValue', 'maxPresValue')
  ORDER BY column_name;
"
# Expected: 7 rows

# 5. Check Prisma status
docker exec bacpipes-frontend sh -c "cd /app && npx prisma migrate status"
# Expected: "Database schema is up to date!"

# 6. Check for errors
docker logs bacpipes-frontend --tail 50 | grep -i error
docker logs bacpipes-worker --tail 50 | grep -i error
# Expected: No critical errors
```

---

### Step 3: Browser Testing

1. **Open:** http://<your-ip>:3001
2. **Dashboard:** Should load WITHOUT "System Error: Failed to fetch dashboard data"
3. **Navigate to:** Points page
4. **Edit a point:** Verify Haystack fields visible (quantity, subject, location, qualifier, dis)
5. **Browser console:** No errors (press F12)

---

## Validation Checklist

Mark each item as you verify:

- [ ] Git pull succeeded
- [ ] Migration file exists: `frontend/prisma/migrations/20251210172641_add_haystack_validation_fields/migration.sql`
- [ ] All Docker services started
- [ ] Frontend logs show "2 migrations found"
- [ ] Database shows 2 migrations in `_prisma_migrations` table
- [ ] All 7 columns exist in Point table
- [ ] Prisma migrate status: "Database schema is up to date!"
- [ ] Dashboard loads at http://<ip>:3001 WITHOUT errors
- [ ] Points page loads and displays points
- [ ] Point editor shows Haystack fields
- [ ] No errors in frontend logs
- [ ] No errors in worker logs
- [ ] MQTT publishing working (if enabled)

---

## Troubleshooting

### If migration doesn't apply automatically:

```bash
# Manually apply migration
docker exec bacpipes-frontend sh -c "cd /app && npx prisma migrate deploy"
```

### If dashboard still shows errors:

```bash
# Check browser console (F12) for specific error
# Check frontend API logs
docker logs bacpipes-frontend | grep -A 5 "dashboard"

# Regenerate Prisma client
docker exec bacpipes-frontend sh -c "cd /app && npx prisma generate"
docker compose restart frontend
```

### If columns are missing:

```bash
# Check actual database schema
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "\d \"Point\""

# Check migration history
docker exec bacpipes-postgres psql -U anatoli -d bacpipes -c "
  SELECT * FROM _prisma_migrations ORDER BY finished_at;
"
```

---

## Success Indicators

You'll know it's working when:

1. ✅ Dashboard loads without "System Error: Failed to fetch dashboard data"
2. ✅ Point editor shows all Haystack tagging fields
3. ✅ No database schema drift warnings
4. ✅ Worker logs show no SQL errors about missing columns
5. ✅ Fresh deployments on new systems work correctly

---

## Technical Details

### Migration File Content

```sql
-- AlterTable: Add Haystack semantic tagging fields
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "quantity" TEXT;
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "subject" TEXT;
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "location" TEXT;
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "qualifier" TEXT;
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "dis" TEXT;

-- AlterTable: Add value range validation fields
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "minPresValue" DOUBLE PRECISION;
ALTER TABLE "Point" ADD COLUMN IF NOT EXISTS "maxPresValue" DOUBLE PRECISION;
```

**Why `IF NOT EXISTS`?**
- Makes migration idempotent (safe to run multiple times)
- Works on existing databases where columns were added manually
- Works on fresh deployments where columns don't exist yet

### Why This Fix Was Needed

The original system had columns added manually via SQL commands without creating Prisma migrations. This created "schema drift" where:
- Existing deployments worked (columns existed)
- Fresh deployments failed (migrations didn't create the columns)
- `prisma migrate reset` would break everything

This migration fixes that by properly tracking the columns in Prisma's migration history.

---

## Rollback (If Needed)

If something goes wrong:

```bash
# Stop services
docker compose down

# Restore from backup (if you created one)
docker exec -i bacpipes-postgres psql -U anatoli -d bacpipes < ~/bacnet-backup-YYYYMMDD-HHMMSS.sql

# Restart services
docker compose up -d
```

Or revert the Git commit:

```bash
git revert a6bf557
docker compose build frontend
docker compose up -d
```

---

## For AI Assistants (Claude)

**Context Summary:**
- Migration created to fix schema drift
- 7 columns added using idempotent SQL
- Frontend container applies migration automatically on startup
- No manual intervention needed for deployment

**Key Actions:**
1. Pull from Gitea development branch
2. Start services with `docker compose up -d`
3. Run verification commands above
4. Confirm checklist items
5. Report success or issues

**Files to Check:**
- Migration: `frontend/prisma/migrations/20251210172641_add_haystack_validation_fields/migration.sql`
- Database: `_prisma_migrations` table (should have 2 rows)
- Database: `Point` table (should have 7 new columns)

---

**Last Updated:** 2025-12-10
**Status:** Ready for deployment on Ubuntu 20 systems
