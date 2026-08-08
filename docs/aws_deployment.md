# AWS Enterprise Deployment & Architecture Guide

## Recommended AWS Architecture Overview

```
                          [AWS Route 53 DNS]
                                  │
                                  ▼
                   [AWS CloudFront / Application Load Balancer]
                                  │
                                  ▼
                   [AWS ECS Fargate Container Service]
                     └── Task: backend container (Port 8000)
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
[AWS RDS PostgreSQL]     [AWS ElastiCache Redis]     [AWS S3 Bucket]
(Relational Users/Sales) (Short-Term Memory)        (Document Uploads)
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                      [AWS Secrets Manager]
              (GROQ_API_KEY, JWT_SECRET, DB_URL)
```

---

## Step-by-Step AWS Deployment Steps

### 1. Amazon ECR (Elastic Container Registry) Setup
Create repository and push production Docker image:
```bash
# 1. Authenticate Docker with AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# 2. Create ECR Repository
aws ecr create-repository --repository-name enterprise-ai-assistant --region us-east-1

# 3. Tag & Push Container Image
docker tag enterprise-ai-assistant:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/enterprise-ai-assistant:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/enterprise-ai-assistant:latest
```

### 2. Managed Database Services
- **AWS RDS PostgreSQL**: Create DB Instance `db.t4g.micro` running PostgreSQL 16 in private subnets.
- **AWS ElastiCache for Redis**: Create Redis cluster `cache.t4g.micro` in private subnets.

### 3. AWS Secrets Manager
Store runtime production credentials in Secrets Manager:
```json
{
  "GROQ_API_KEY": "gsk_...",
  "TAVILY_API_KEY": "tvly-...",
  "DATABASE_URL": "postgresql://postgres:<password>@<rds-endpoint>:5432/enterprise_db",
  "REDIS_URL": "redis://<elasticache-endpoint>:6379/0",
  "JWT_SECRET": "<generated_random_secret_key>"
}
```

### 4. AWS ECS Fargate Task Definition
Define Task Definition with container image from ECR and environment variables sourced from Secrets Manager:
- CPU: `1 vCPU` (1024)
- Memory: `2 GB` (2048)
- Port Mappings: `8000`
- Health Check Path: `/health/ready`

### 5. Application Load Balancer (ALB) & Health Check Target Group
Configure Target Group pointing to ECS Task port 8000:
- **Health Check Path**: `/health/ready`
- **Success Code**: `200`
- **Interval**: `30s`
- **Timeout**: `5s`
