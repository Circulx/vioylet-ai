# AWS Storage Deployment

This backend now supports separate local and server storage modes.

## Local mode

Use this when developing on your machine:

```env
OBJECT_STORAGE_PROVIDER=local
OBJECT_STORAGE_BASE_PATH=./storage
VECTOR_STORE_PROVIDER=faiss
VECTOR_STORE_BASE_PATH=./vector_store
GENERATED_ASSETS_BASE_URL=http://localhost:8000/storage
ASSET_DOWNLOAD_BASE_URL=http://localhost:8000/api/v1/storage/download
EXPOSE_PUBLIC_STORAGE=true
```

Local mode stores uploaded files, generated images, rendered exports, and FAISS indexes on disk.

## AWS/server mode

Use this when deploying to AWS:

```env
OBJECT_STORAGE_PROVIDER=s3
OBJECT_STORAGE_CACHE_PATH=/tmp/violyt-object-storage-cache
AWS_REGION=ap-south-1
AWS_S3_BUCKET=your-violyt-bucket
AWS_S3_PREFIX=violyt
VECTOR_STORE_PROVIDER=pgvector
GENERATED_ASSETS_BASE_URL=http://your-domain-or-ip/storage
ASSET_DOWNLOAD_BASE_URL=http://your-domain-or-ip/api/v1/storage/download
EXPOSE_PUBLIC_STORAGE=true
```

Server mode stores durable binary assets in S3 and retrieval documents in Postgres through pgvector.

## Storage split

S3:
- Uploaded brand files, templates, knowledge documents, logos, fonts, and tenant assets
- Generated preview/export images and documents
- AI image-generation outputs

Postgres/pgvector:
- Retrieval chunks
- Retrieval metadata
- Embeddings used for knowledge search

Server local disk:
- Temporary S3 cache under `OBJECT_STORAGE_CACHE_PATH`
- Generation traces under `GENERATION_TRACE_BASE_PATH`
- Application logs

The S3 cache is disposable. If the container is recreated, files are downloaded again from S3 when needed.

## Required AWS permissions

The API and worker need access to the configured bucket:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject",
    "s3:HeadObject"
  ],
  "Resource": "arn:aws:s3:::your-violyt-bucket/*"
}
```

Use an EC2 instance profile or ECS task role where possible. If credentials are provided by environment variables, keep them out of the repo.
