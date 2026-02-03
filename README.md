# Elaas Backend

FastAPI application with Supabase (PostgreSQL) and Kafka integration.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and configure:
```bash
cp .env.example .env
```

3. Update `.env` with your Supabase and Kafka credentials.

## Running

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`

## Features

- FastAPI REST API
- Supabase SDK for PostgreSQL operations
- Kafka producer/consumer for message brokering
- Environment-based configuration
- Example CRUD operations with messages

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/messages` - Create message
- `GET /api/v1/messages` - List messages
- `GET /api/v1/messages/{id}` - Get message by ID

## Kafka Topics

Messages are published to: `{KAFKA_TOPIC_PREFIX}.messages`

## Deployment options

<details>
<summary><strong>AWS EC2 (VM)</strong></summary>

Run the backend as a Docker container on an Amazon Linux 2 or Ubuntu EC2 instance (or any Linux VM).

## Prerequisites

- **EC2 instance**: Amazon Linux 2 or Ubuntu 22.04, with inbound TCP **8080** (and 22 for SSH) in the security group.
- **Docker** on the VM (install below if needed).

## 1. Launch and connect to the VM

- Launch an EC2 instance (e.g. `t3.small` or larger; ensure enough memory for Terraform/Gunicorn).
- Security group: allow inbound **22** (SSH) and **8080** (app).
- SSH in: `ssh -i your-key.pem ec2-user@<public-ip>` (Amazon Linux) or `ubuntu@<public-ip>` (Ubuntu).

## 2. Install Docker (if not present)

**Amazon Linux 2:**

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in (or new SSH session) so docker runs without sudo
```

**Ubuntu:**

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
# Log out and back in
```

## 3. Deploy the application

```bash
# Clone the repo (or copy files onto the VM)
git clone <your-repo-url> elaas-backend && cd elaas-backend

# Configure environment
cp .env.example .env
# Edit .env with your Supabase, Kafka, AWS (S3), and app settings (see .env.example)

# Run with the script (builds image and starts container)
chmod +x scripts/run-on-aws-vm.sh
./scripts/run-on-aws-vm.sh
```

The app listens on **port 8080**. Check health: `curl http://localhost:8080/health`.

## 4. Script options

| Invocation | Description |
|------------|-------------|
| `./scripts/run-on-aws-vm.sh` or `./scripts/run-on-aws-vm.sh --build` | Build image and run container (default). |
| `IMAGE=<ecr-uri> ./scripts/run-on-aws-vm.sh --pull` | Pull image from ECR and run (see below). |
| `./scripts/run-on-aws-vm.sh --compose` | Run with `docker compose up -d` (uses `docker-compose.yml`). |

Optional env vars: `CONTAINER_NAME`, `IMAGE_NAME`, `PORT`, `ENV_FILE`. Example: `PORT=8080 ./scripts/run-on-aws-vm.sh`.

## 5. Using a pre-built image (e.g. ECR)

Build and push the image from your machine or CI:

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t elaas-backend:latest .
docker tag elaas-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/elaas-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/elaas-backend:latest
```

On the VM, attach an IAM role with `AmazonEC2ContainerRegistryReadOnly` (or equivalent), then:

```bash
aws ecr get-login-password --region us-east-1 | sudo docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
IMAGE=<account-id>.dkr.ecr.us-east-1.amazonaws.com/elaas-backend:latest ./scripts/run-on-aws-vm.sh --pull
```

## 6. Managing the container

- **Logs:** `docker logs -f elaas-backend`
- **Restart:** `docker restart elaas-backend`
- **Stop:** `docker stop elaas-backend`
- **Update (rebuild and run):** `./scripts/run-on-aws-vm.sh` (stops existing container, rebuilds, runs)

The script uses `--restart unless-stopped`, so the container starts again after a VM reboot.

## 7. Future extensions

- **Add services (e.g. Kafka):** Add another service in `docker-compose.yml` and run with `./scripts/run-on-aws-vm.sh --compose`.
- **Secrets:** Use AWS Secrets Manager or SSM Parameter Store and inject env vars (e.g. with a small wrapper or `docker run` env from `aws ssm get-parameters`).
- **HTTPS:** Put a reverse proxy (e.g. Nginx or Caddy) or an ALB in front of the VM and terminate TLS there.

</details>

<details>
<summary><strong>Google Cloud Run</strong></summary>

This section describes how to deploy elaas-backend to **Google Cloud Run** using the provided Dockerfile and deploy script.

## Prerequisites

- [Google Cloud SDK (gcloud)](https://cloud.google.com/sdk/docs/install) installed and logged in
- A GCP project with **Cloud Run** and **Cloud Build** APIs enabled
- (Optional) Docker installed locally if you want to build/test the image locally

### Enable APIs

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### Authenticate

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

## Build & Run Locally with Docker

```bash
docker build -t elaas-backend .
docker run -p 8080:8080 --env-file .env elaas-backend
```

Visit `http://localhost:8080`. The container reads `PORT` from the environment (default 8080).

## Deployment Options

### Option 1: Deploy with the script (recommended)

From the project root:

```bash
chmod +x scripts/deploy-cloud-run.sh
./scripts/deploy-cloud-run.sh
```

With options:

```bash
./scripts/deploy-cloud-run.sh -p YOUR_PROJECT_ID -r us-central1 -s elaas-backend
```

Environment variables (optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT` | `gcloud config get-value project` | GCP project ID |
| `REGION` | `us-central1` | Cloud Run region |
| `SERVICE_NAME` | `elaas-backend` | Cloud Run service name |
| `ALLOW_UNAUTHENTICATED` | `true` | Allow unauthenticated HTTP requests |
| `MEMORY` | `512Mi` | Memory per instance |
| `CPU` | `1` | CPU per instance |
| `MIN_INSTANCES` | `0` | Min instances (0 = scale to zero) |
| `MAX_INSTANCES` | `10` | Max instances |

Example with custom memory/CPU:

```bash
MEMORY=1Gi CPU=2 ./scripts/deploy-cloud-run.sh -p my-project
```

### Option 2: Deploy with gcloud only

```bash
gcloud run deploy elaas-backend \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080
```

Cloud Build will use the repository `Dockerfile` and deploy the resulting image to Cloud Run.

## Configuring environment variables and secrets

The app uses settings from environment variables (see `.env.example` and `app/config/settings.py`). On Cloud Run you must provide these via **environment variables** or **Secret Manager**.

### Set env vars at deploy time

```bash
gcloud run deploy elaas-backend \
  --source . \
  --region us-central1 \
  --set-env-vars "SUPABASE_URL=https://xxx.supabase.co,SUPABASE_KEY=anon_key_here,SUPABASE_SERVICE_ROLE_KEY=service_role_here"
```

### Use Secret Manager (recommended for production)

1. Create secrets:

```bash
echo -n "https://your-project.supabase.co" | gcloud secrets create supabase-url --data-file=-
echo -n "your-anon-key" | gcloud secrets create supabase-key --data-file=-
echo -n "your-service-role-key" | gcloud secrets create supabase-service-role-key --data-file=-
```

2. Grant Cloud Run access and deploy with secrets:

```bash
gcloud run deploy elaas-backend \
  --source . \
  --region us-central1 \
  --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_KEY=supabase-key:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest"
```

The Cloud Run service’s identity must have `roles/secretmanager.secretAccessor` on these secrets (or on the project). When using `--set-secrets`, Cloud Run configures the default compute service account; ensure that account has secret access.

## After deployment

- **URL**: Shown at the end of `gcloud run deploy` or:

  ```bash
  gcloud run services describe elaas-backend --region us-central1 --format 'value(status.url)'
  ```

- **Health**: `GET https://YOUR_SERVICE_URL/health`
- **Logs**: `gcloud run services logs read elaas-backend --region us-central1`

## Dockerfile details

- **Base image**: `python:3.12-slim`
- **Port**: 8080 (Cloud Run sets `PORT`; the app uses it)
- **Entrypoint**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Build context**: `app/`, `requirements.txt` (see `.dockerignore` for exclusions)

## Troubleshooting

| Issue | Check |
|-------|--------|
| Build fails | Ensure `requirements.txt` and `app/` are present; run `docker build -t elaas-backend .` locally |
| 503 / not listening | App must listen on `0.0.0.0` and the port given by `PORT` (done in Dockerfile CMD) |
| Env vars not applied | Set via `--set-env-vars` or `--set-secrets`; do not rely on `.env` in the image |
| Permission denied (secrets) | Grant the Cloud Run service account `roles/secretmanager.secretAccessor` on the secrets |

</details>
