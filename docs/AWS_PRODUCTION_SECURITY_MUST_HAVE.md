# AWS Production Security Must-Haves

## Purpose

This document lists only the AWS security measures that are most important when Violyt is published for real users in production.

These are not required for local development. They are recommended for production deployment on AWS because the platform handles:

- user login and activation
- tenant and Brand Space data
- uploaded brand assets
- generated PDF/JPG/PNG/DOC assets
- AI provider keys
- email credentials
- PostgreSQL data
- public-facing API traffic

Cost notes are approximate and depend on AWS region, traffic, storage, architecture, and log volume. Always verify final pricing in the AWS console/pricing pages before deployment.

## Must-Have Production Controls

### 1. IAM Least Privilege

**What to implement**

- Separate IAM roles for backend, worker, deployment, and operational access.
- Do not use AWS root or admin credentials for application runtime.
- Give each service only the permissions it needs.

**How it helps**

Prevents one leaked credential or one compromised service from taking over the whole AWS account.

**Approximate security cost**

```text
$0/month
```

IAM itself has no direct monthly charge.

### 2. Secrets Manager or SSM Parameter Store

**What to implement**

Store production secrets outside code and outside server `.env` files:

- `SECRET_KEY`
- database password
- SMTP credentials
- OpenAI/Anthropic keys
- social encryption key
- third-party API keys

**How it helps**

Reduces risk of leaked credentials in code, logs, server files, or deployment pipelines. It also makes future key rotation easier.

**Approximate security cost**

```text
Secrets Manager: about $0.40 per secret/month + API calls
Small production estimate: $5-$15/month
```

For lower-cost setups, SSM Parameter Store can be used for some values, but Secrets Manager is better for high-value credentials and rotation workflows.

### 3. Private VPC, Private Database, and Security Groups

**What to implement**

- Put RDS/PostgreSQL in private subnets.
- Do not expose the database publicly.
- Allow backend traffic only from the load balancer.
- Allow database traffic only from backend/worker security groups.
- Keep security group rules narrow.

**How it helps**

Prevents direct internet access to the database and limits lateral movement if one component is compromised.

**Approximate security cost**

```text
Security groups/VPC controls: $0/month
NAT Gateway, load balancer, and data transfer may add infrastructure cost depending on deployment design.
```

### 4. HTTPS/TLS with AWS Certificate Manager

**What to implement**

- Use HTTPS for the frontend, backend API, activation links, asset links, and review links.
- Use AWS Certificate Manager certificates with ALB or CloudFront.
- Redirect HTTP to HTTPS.

**How it helps**

Protects login credentials, JWTs, activation tokens, signed asset URLs, and user data in transit.

**Approximate security cost**

```text
ACM public certificates used with AWS integrated services: usually $0/month
ALB/CloudFront costs are separate infrastructure costs.
```

### 5. Private S3 Buckets and Signed Asset Access

**What to implement**

- Use private S3 buckets for uploaded and generated assets.
- Enable Block Public Access.
- Do not serve assets through public bucket URLs.
- Use signed URLs or backend-controlled download routes.
- Enable default bucket encryption.

**How it helps**

Prevents accidental public exposure of brand documents, generated files, logos, and uploaded assets.

**Approximate security cost**

```text
S3 Block Public Access/default encryption: no separate security fee
S3 storage and requests: usage-based
Optional KMS key: about $1/key/month + API usage
```

### 6. RDS Encryption, Backups, and Private Access

**What to implement**

- Enable encryption at rest for PostgreSQL/RDS.
- Keep RDS in private subnets.
- Enable automated backups.
- Restrict access by security group.
- Use strong database credentials from Secrets Manager/SSM.

**How it helps**

Protects tenant data, user records, chat history, generated content metadata, activation tokens, and analytics if storage or snapshots are exposed.

**Approximate security cost**

```text
RDS encryption: no separate feature fee
Automated backup storage: often included up to allocated DB size; extra backup storage is usage-based
RDS instance/storage cost remains the main cost
```

### 7. CloudWatch Logs and Basic Alarms

**What to implement**

Send backend, worker, and deployment logs to CloudWatch.

Create alarms for:

- high `5xx` errors
- high `4xx` errors
- backend crashes
- failed jobs
- high CPU/memory
- abnormal API latency

**How it helps**

Lets the team detect production failures, suspicious spikes, and operational issues quickly.

**Approximate security cost**

```text
Small production estimate: $5-$25/month
Cost depends on log volume, retention period, and number of alarms.
```

### 8. CloudTrail

**What to implement**

- Enable CloudTrail for AWS account activity.
- Store logs in S3.
- Monitor sensitive events such as IAM changes, S3 policy changes, secret access, and security group changes.

**How it helps**

Provides an audit trail for AWS account changes and helps investigate security incidents.

**Approximate security cost**

```text
Management event history: available by default
One trail for management events: commonly low cost; S3 storage charges apply
Small production estimate: $2-$10/month
```

### 9. AWS WAF Basic Managed Rules and Rate Limiting

**What to implement**

Place AWS WAF in front of the public entry point, usually CloudFront, ALB, or API Gateway.

Use:

- AWS managed common rule set
- SQL injection rules
- known bad input rules
- rate-based rule for login/API abuse
- optional IP blocking for repeated abuse

**How it helps**

Protects the public app/API from common web attacks, bot traffic, abusive request bursts, and brute-force-style traffic.

**Approximate security cost**

```text
Web ACL: about $5/month
Rules: about $1/rule/month
Requests: about $0.60 per 1 million inspected requests
Small production estimate: $15-$50/month
```

### 10. ECR Image Scanning

**What to implement**

If Violyt is deployed with Docker/ECR:

- enable ECR image scanning
- block deployment of images with critical vulnerabilities when possible
- keep base images updated

**How it helps**

Reduces the risk of shipping vulnerable OS packages or application dependencies into production.

**Approximate security cost**

```text
ECR basic scanning: commonly available without separate per-scan cost
Enhanced scanning has additional usage-based cost
```

### 11. Environment Separation

**What to implement**

Keep separate production, staging, and development resources:

- separate databases
- separate buckets
- separate secrets
- separate IAM roles
- separate frontend/backend URLs

**How it helps**

Prevents development mistakes from affecting production data and keeps test secrets/data away from real customers.

**Approximate security cost**

```text
No direct security feature fee
Extra environments increase normal infrastructure cost.
```

## Estimated Security Cost for Small Production

For a small public production deployment, the must-have AWS security layer is likely to add roughly:

```text
IAM:                 $0
Secrets:             $5-$15
VPC/Security Groups: $0 security fee
ACM TLS:             $0 certificate fee
S3 security:         $0 security fee, storage/request costs separate
RDS security:        $0 security fee, RDS cost separate
CloudWatch:          $5-$25
CloudTrail:          $2-$10
AWS WAF:             $15-$50
ECR scanning:        $0 for basic scanning
Environment split:   infrastructure-dependent
-----------------------------------------------
Estimated add-on:    about $25-$100/month
```

This estimate excludes the normal cost of the application infrastructure itself, such as RDS, ECS/EC2, ALB, NAT Gateway, S3 storage, CloudFront, and AI provider usage.

## Not Required Immediately

The following are useful later, but not part of the must-have minimum for the current production pipeline:

- Security Hub
- Shield Advanced
- enterprise SIEM integration
- multi-account AWS Organizations security setup
- advanced GuardDuty tuning
- automated compliance reporting

AWS Shield Standard is already included for supported AWS services. Shield Advanced is usually not needed unless the platform becomes high-risk, high-traffic, or enterprise-critical.

## Summary

For Violyt production on AWS, the most important security controls are:

1. IAM least privilege
2. Secrets Manager or SSM
3. Private VPC, private RDS, and security groups
4. HTTPS/TLS with ACM
5. Private S3 with signed access
6. RDS encryption and backups
7. CloudWatch logs and alarms
8. CloudTrail
9. AWS WAF basic managed rules and rate limiting
10. ECR image scanning if Docker/ECR is used
11. separate environments for dev, staging, and production

These controls cover the most realistic production risks without adding unnecessary AWS security complexity too early.
