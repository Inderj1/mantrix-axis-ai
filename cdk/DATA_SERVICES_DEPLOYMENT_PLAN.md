# Data Services Deployment Plan

## Executive Summary

We're trying to deploy MongoDB and Weaviate as persistent data services for Mantrix AI on AWS ECS Fargate. The deployment has been failing due to EFS (Elastic File System) permission issues that prevent the containers from writing to their data directories.

---

## What We're Building

### Architecture Overview

```
                                    ┌─────────────────────────────────────┐
                                    │         ECS Cluster                 │
                                    │         (mantrix-dev)               │
                                    │                                     │
┌──────────────┐                    │  ┌─────────────────────────────┐   │
│   Backend    │───Cloud Map DNS───▶│  │   Data Services Task        │   │
│   Service    │                    │  │   (PRIVATE_ISOLATED subnet) │   │
└──────────────┘                    │  │                             │   │
       │                            │  │  ┌─────────┐  ┌──────────┐  │   │
       │                            │  │  │ MongoDB │  │ Weaviate │  │   │
       │                            │  │  │  :27017 │  │  :8080   │  │   │
       │                            │  │  └────┬────┘  └────┬─────┘  │   │
       │                            │  │       │            │        │   │
       │                            │  └───────┼────────────┼────────┘   │
       │                            │          │            │            │
       │                            └──────────┼────────────┼────────────┘
       │                                       │            │
       │                                       ▼            ▼
       │                            ┌─────────────────────────────────────┐
       │                            │           AWS EFS                   │
       │                            │    (fs-06425bc4e0e6eb7b1)          │
       │                            │                                     │
       │                            │  /data-services/mongodb  (UID 999) │
       │                            │  /data-services/weaviate (UID 0)   │
       │                            └─────────────────────────────────────┘
       │
       └────────▶ mongodb://data-services.mantrix-dev.local:27017
                  http://data-services.mantrix-dev.local:8080
```

### Components

| Component | Purpose | Port | Container UID |
|-----------|---------|------|---------------|
| MongoDB 7.0 | Conversation history, market signals storage | 27017 | 999 (mongodb user) |
| Weaviate 1.24 | Vector embeddings for semantic search | 8080 | 0 (root) |

### Service Discovery

- **Cloud Map Namespace**: `mantrix-dev.local`
- **Service DNS**: `data-services.mantrix-dev.local`
- Backend connects via internal DNS, no public exposure

---

## Current Failure Analysis

### Error Message

```
MongoDB: "Permission denied: /data/db/journal"
Weaviate: "permission denied: /var/lib/weaviate/schema.db"
```

### Root Cause

**The Problem**: We configured a single EFS Access Point with UID/GID 999 for both containers.

| Container | Expected UID | Access Point UID | Result |
|-----------|--------------|------------------|--------|
| MongoDB | 999 | 999 | Should work, but fails |
| Weaviate | 0 (root) | 999 | Permission denied |

**Why MongoDB also fails**: Even though MongoDB runs as UID 999, the EFS directory `/data-services` was likely created with different initial ownership, or the access point `posixUser` enforcement isn't working as expected.

### Timeline of Issues Fixed

| Issue | Fix Applied | Status |
|-------|-------------|--------|
| EFS AccessPoint TypeScript error | Fixed type annotation | ✅ Resolved |
| ECR authorization error | Added ECR policy to execution role | ✅ Resolved |
| EFS mount timeout | Added NFS security group rule (port 2049) | ✅ Resolved |
| S3 access from isolated subnets | Added S3 gateway endpoint routes | ✅ Resolved |
| MongoDB EFS permission (UID 999) | Set user: '999:999' on container | ❌ Still failing |
| Weaviate EFS permission (UID 0) | Created separate access points | ❌ Not deployed yet |

### Current Blocker

The fix for separate EFS access points is in the local code but **never got deployed** because:
1. A CDK CLI conflict prevented the deployment
2. The CloudFormation stack got stuck in `UPDATE_IN_PROGRESS` for 3+ hours
3. ECS kept restarting failing containers indefinitely

---

## Proposed Solutions

### Option A: Simplified EFS Approach (Recommended)

**Strategy**: Remove Weaviate's EFS dependency, use ephemeral storage for Weaviate.

**Rationale**:
- Weaviate data can be rebuilt from the backend's schema pipeline
- Only MongoDB truly needs persistence
- Reduces complexity significantly

**Changes Required**:
1. Keep MongoDB with EFS access point (UID 999)
2. Remove Weaviate EFS volume mount
3. Weaviate uses ephemeral container storage (data rebuilds on restart)

**Pros**:
- Simpler permission model
- Faster deployment
- Weaviate schema rebuilds automatically via pipeline scheduler

**Cons**:
- Weaviate data lost on container restart (acceptable for dev)
- Need to run schema pipeline after restart

---

### Option B: Separate EFS Access Points (Current Approach)

**Strategy**: Create dedicated EFS access points for each container with correct UID/GID.

**Implementation** (already in code):
```typescript
// MongoDB: UID 999
const mongoAccessPoint = new efs.AccessPoint(this, 'MongoDBAccessPoint', {
  fileSystem: props.efsFileSystem,
  path: '/data-services/mongodb',
  posixUser: { uid: '999', gid: '999' },
  createAcl: { ownerUid: '999', ownerGid: '999', permissions: '755' },
});

// Weaviate: UID 0 (root)
const weaviateAccessPoint = new efs.AccessPoint(this, 'WeaviateAccessPoint', {
  fileSystem: props.efsFileSystem,
  path: '/data-services/weaviate',
  posixUser: { uid: '0', gid: '0' },
  createAcl: { ownerUid: '0', ownerGid: '0', permissions: '755' },
});
```

**Pros**:
- Full persistence for both services
- Production-ready architecture

**Cons**:
- More complex
- Requires careful permission management
- Longer debug cycles

---

### Option C: Use Managed Services (Simplest)

**Strategy**: Replace self-hosted MongoDB/Weaviate with managed services.

| Service | Managed Alternative | Free Tier |
|---------|---------------------|-----------|
| MongoDB | MongoDB Atlas | 512MB free |
| Weaviate | Weaviate Cloud | Free sandbox |

**Pros**:
- No infrastructure to manage
- Automatic backups, scaling
- Eliminates EFS complexity entirely

**Cons**:
- External dependencies
- Data leaves your VPC
- May have latency impact

---

### Option D: Use EBS Instead of EFS

**Strategy**: Use EBS volumes for persistent storage.

**Pros**:
- Simpler permission model (standard Linux)
- Better performance for databases

**Cons**:
- Single AZ only (EBS volumes are AZ-specific)
- Requires EC2 launch type or ECS on EC2
- Not compatible with Fargate

---

## Recommended Approach

**Recommendation: Option A (Simplified EFS)**

This balances reliability with the existing architecture:

1. **Phase 1**: Deploy with MongoDB EFS only, Weaviate ephemeral
2. **Phase 2**: Once stable, optionally add Weaviate EFS if needed
3. **Phase 3**: For production, consider Option C (managed services)

---

## Implementation Steps

### Pre-Deployment Checklist

- [ ] Cancel any stuck CloudFormation updates
- [ ] Wait for stack to reach stable state (UPDATE_COMPLETE or UPDATE_ROLLBACK_COMPLETE)
- [ ] Clear CDK output directory to avoid CLI conflicts
- [ ] Verify EFS file system exists and is accessible

### Deployment Steps

1. **Modify application-stack.ts**:
   - Keep MongoDB with EFS mount
   - Remove Weaviate EFS volume mount
   - Set Weaviate to use ephemeral storage

2. **Deploy with desiredCount: 0**:
   - Creates all infrastructure without starting containers
   - Allows verification of EFS access points

3. **Verify EFS Setup**:
   ```bash
   # Check access points exist
   aws efs describe-access-points --file-system-id fs-06425bc4e0e6eb7b1

   # Verify mount targets in correct subnets
   aws efs describe-mount-targets --file-system-id fs-06425bc4e0e6eb7b1
   ```

4. **Scale Up Service**:
   ```bash
   aws ecs update-service --cluster mantrix-dev \
     --service mantrix-dev-data-services \
     --desired-count 1
   ```

5. **Monitor Container Logs**:
   ```bash
   aws logs tail /ecs/mantrix-dev/data-services --follow
   ```

### Rollback Plan

If deployment fails:
1. Scale service to 0: `aws ecs update-service --desired-count 0`
2. Check logs for specific error
3. Fix configuration
4. Redeploy

---

## Testing Verification

### Success Criteria

1. **ECS Service**: `runningCount: 1`, `desiredCount: 1`
2. **MongoDB**: Accepting connections on port 27017
3. **Weaviate**: Health check passing on port 8080
4. **Backend**: Can connect to both services via Cloud Map DNS

### Test Commands

```bash
# Check service status
aws ecs describe-services --cluster mantrix-dev --services mantrix-dev-data-services

# Test MongoDB (from backend container)
mongosh mongodb://data-services.mantrix-dev.local:27017/nlp_sql_db --eval "db.runCommand({ping: 1})"

# Test Weaviate health
curl http://data-services.mantrix-dev.local:8080/v1/.well-known/ready
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| EFS permissions still fail | Medium | High | Option A removes Weaviate EFS |
| Container OOM | Low | Medium | Monitor memory, adjust limits |
| EFS mount timeout | Low | High | VPC endpoints already configured |
| Network connectivity | Low | Medium | Security groups verified |

---

## Decision Required

Please choose which option to proceed with:

- **Option A**: MongoDB with EFS, Weaviate ephemeral (Recommended)
- **Option B**: Both with separate EFS access points (Current code)
- **Option C**: Use managed MongoDB Atlas + Weaviate Cloud
- **Other**: Suggest alternative approach

Once you confirm, I'll implement the chosen approach.
