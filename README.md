# Travel Simulator

## Introduction

Travel Simulator is a system for testing proposed London transport stations and estimating their effect on coverage, passenger journeys, and route-level travel times.

The project combines:
- TfL station and network data
- AWS infrastructure
- an AWS Lambda simulation engine
- S3 storage for processed data and simulation outputs
- a Streamlit dashboard for client-facing analysis
- Google Earth Engine land-use analysis
- OpenAI-assisted report generation
- KML/KMZ exports for Google Earth Pro

The dashboard allows a user to select a proposed station location, choose a rail line, run the simulation, view affected routes and charts, download a recommendation PDF, and export a Google Earth-compatible KMZ file.

---

## Repository Structure

```text
travel-simulator/
├── choropleth/
├── dashboard/
├── infrastructure/
├── simulation/
├── tfl_data_and_network/
└── README.md
```

### `dashboard/`

Streamlit dashboard used by the end user.

Key files:
- `dashboard.py` - main Streamlit dashboard
- `analysis.py` - land-use analysis and report generation
- `coverage_context.py` - coverage calculation around a proposed station
- `df_analysis.py` - simulation metrics, affected routes, and Altair charts
- `folium_functions.py` - post-simulation Folium map functions
- `kml_export.py` - KML/KMZ export logic
- `s3_utils.py` - reads simulation outputs and station data from S3
- `stations_choropleth.py` - borough choropleth and transport network map

### `simulation/`

AWS Lambda simulation engine.

Key files:
- `run_sim_and_save.py` - main simulation runner
- `collect_passengers.py` - passenger collection logic
- `distance_maths.py` - distance and route calculations
- `result_analysis.py` - simulation result processing
- `s3_utils_sim.py` - S3 utilities used by the simulation

### `tfl_data_and_network/`

TfL data extraction and network graph creation.

Key files:
- `api_utils.py`
- `get_lines.py`
- `get_sequenced_stops.py`
- `get_travel_times.py`
- `create_stations_network.py`
- `connect_nearby_stations.py`

### `infrastructure/`

Terraform and deployment scripts for AWS.

This folder creates and manages:
- S3 bucket
- ECR repositories
- Lambda functions
- ECS dashboard service
- IAM roles and policies
- API Gateway, if enabled
- required environment variables for deployed services

---

## Prerequisites

Install the following locally:

```bash
python --version
terraform --version
aws --version
docker --version
```

Recommended versions:
- Python 3.11+
- Terraform 1.0+
- Docker Desktop
- AWS CLI v2

You also need:
- AWS credentials configured locally
- access to the AWS account used by the project
- a Google Cloud project with Earth Engine enabled
- an OpenAI API key if using AI-generated report wording

---

## 1. Clone the Repository

```bash
git clone <repo-url>
cd travel-simulator
```

---

## 2. Create a Python Virtual Environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dashboard dependencies:

```bash
pip install -r dashboard/requirements.txt
```

If there is a root-level requirements file, also run:

```bash
pip install -r requirements.txt
```

---

## 3. Configure AWS Locally

The local machine needs AWS credentials so Terraform can create infrastructure and the dashboard can read S3 / invoke Lambda during local testing.

Check your identity:

```bash
aws sts get-caller-identity
```

If this fails, configure credentials:

```bash
aws configure
```

Use region:

```text
eu-west-2
```

---

## 4. Create the Local `.env` File

Create a `.env` file in the repository root:

```bash
touch .env
```

### Required `.env` values

| Variable | Required locally? | Required in ECS? | Purpose |
|---|---:|---:|---|
| `S3_BUCKET_NAME` | Yes | Yes | S3 bucket containing processed station data and simulation outputs |
| `SIMULATION_LAMBDA_ARN` | Yes, if invoking Lambda locally | Yes | Lambda ARN for the simulation engine |
| `GOOGLE_CLOUD_PROJECT` | Yes | Yes | Google Cloud project used for Earth Engine |
| `OPENAI_API_KEY` | Yes, if generating AI reports | Yes, if generating AI reports | Used by `analysis.py` for client-ready report wording |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | No for local dev if using `earthengine authenticate` | Yes | Full Google service account JSON for Earth Engine in ECS |

### Local Google Earth Engine authentication

For local development, the easiest setup is:

```bash
earthengine authenticate
```

Then keep this in `.env`:

```env
GOOGLE_CLOUD_PROJECT=travel-simulation-497813
```

Do **not** put `GOOGLE_APPLICATION_CREDENTIALS_JSON` in your local `.env` unless you are testing service-account authentication locally.

### ECS Google Earth Engine authentication

In ECS, `earthengine authenticate` cannot be used because the container cannot open a browser or use `gcloud`.

For ECS, set:

```env
S3_BUCKET_NAME=s3-bucket-name
GOOGLE_CLOUD_PROJECT=google-cloud-project-id
OPENAI_API_KEY=your_openai_api_key_here
SIMULATION_LAMBDA_ARN=arn:aws:lambda:eu-west-2:<aws-account-id>:function:simulation-lambda-name
GOOGLE_APPLICATION_CREDENTIALS_JSON={full service account json}
```

Prefer storing this value in AWS Secrets Manager and injecting it into the ECS task definition as a secret.

Do not commit `.env`, service account JSON files, API keys, or Terraform variable files containing secrets.

---

## 5. Terraform Setup from Scratch

Go to the infrastructure folder:

```bash
cd infrastructure
```

Initialise Terraform:

```bash
terraform init
```

Check what Terraform will create:

```bash
terraform plan
```

Apply the infrastructure:

```bash
terraform apply -target=module.networkx_lambda
terraform apply -target aws_ecr_repository.c23_travel_simulator_simulation
terraform apply -target aws_ecr_repository.c23_travel_simulator_choropleth_pipeline
terraform apply -target aws_ecr_repository.c23_travel_simulator_dashboard_ecr
```

This step is required locally before the deployment scripts can work because the scripts use Terraform outputs such as ECR repository URLs.

After apply, inspect outputs:

```bash
terraform output
```

Expected outputs may include:
- ECR repository URL for the dashboard
- ECR repository URL for the simulation Lambda
- Lambda ARN
- ECS service information
- S3 bucket name

---

## 5.5. Setup Initial Data Pipelines

Before building and deploying services, the TfL network graph and choropleth boundary data must be prepared. These are prerequisites for the dashboard.

### Choropleth Boundary Setup (Local)

The choropleth pipeline generates borough-level station density maps. It requires borough boundary data:

From the repository root, go to the choropleth folder:

```bash
cd choropleth
pip install -r requirements.txt
bash download_boundaries.sh
```

---

## 6. Build and Push Docker Images

All deployment scripts should be run from inside the `infrastructure/` folder unless stated otherwise.

```bash
cd infrastructure
```

### Deploy the NetworkX pipeline image

```bash
bash deploy_networkx.sh
```

This builds and pushes the NetworkX image.

### Deploy the choropleth Lambda image

```bash
bash deploy_choropleth.sh
```

This builds and pushes the choropleth image.

### Deploy the simulation Lambda image

```bash
bash deploy_simulation.sh
```

This builds and pushes the simulation image.

### Deploy the dashboard image

```bash
bash dashboard.sh
```

The dashboard script:
1. gets the ECR dashboard repository URL from Terraform outputs
2. logs in to ECR
3. builds the dashboard Docker image
4. tags the image as `latest`
5. pushes it to ECR
6. forces an ECS service redeployment

If the script is not executable, run:

```bash
chmod +x dashboard.sh
./dashboard.sh
```

## 7. Apply Terraform Again After Image Pushes

After the first image push, run:

```bash
terraform plan
terraform apply
```

This ensures the Lambda functions, ECS task definitions, environment variables, and IAM policies point to the correct deployed resources.

---

---

### Invoke Lambda

```bash
aws lambda invoke --function-name c23-travel-simulator-simulation response.json
aws logs tail /aws/lambda/c23-travel-simulator-simulation --follow

aws lambda invoke --function-name c23-travel-simulator-choropleth-pipeline response.json
aws logs tail /aws/lambda/c23-travel-simulator-choropleth-pipeline --follow
```


## 9. ECS Environment Variables

The dashboard ECS task needs these environment variables:

```env
S3_BUCKET_NAME=c23-travel-simulation-bucket
SIMULATION_LAMBDA_ARN=arn:aws:lambda:eu-west-2:<aws-account-id>:function:c23-travel-simulator-simulation
GOOGLE_CLOUD_PROJECT=travel-simulation-497813
OPENAI_API_KEY=your_openai_api_key_here
```

The dashboard ECS task also needs this secret:

```env
GOOGLE_APPLICATION_CREDENTIALS_JSON={full Google service account JSON}
```

Recommended setup:
- Store `GOOGLE_APPLICATION_CREDENTIALS_JSON` in AWS Secrets Manager
- Inject it into the ECS task definition as a secret
- Do not put it directly in GitHub or Dockerfiles

---

## 9. IAM Permissions Required

The ECS dashboard task role needs permission to:
- read from S3
- write/read relevant dashboard outputs if required
- invoke the simulation Lambda

The dashboard task role must include:

```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:InvokeFunction"
  ],
  "Resource": "arn:aws:lambda:eu-west-2:<aws-account-id>:function:c23-travel-simulator-simulation"
}
```

The simulation Lambda role needs permission to:
- read processed data from S3
- write simulation outputs back to S3
- write CloudWatch logs

---

## 10. Run the Dashboard Locally

From the repository root:

```bash
streamlit run dashboard/dashboard.py
```

The dashboard opens at:

```text
http://localhost:8501
```

Local dashboard requirements:
- `.env` exists in the repository root
- AWS credentials are configured
- Terraform has been applied at least once
- `SIMULATION_LAMBDA_ARN` is set if running the real Lambda
- `S3_BUCKET_NAME` is set
- Earth Engine has been authenticated locally

---

## 11. Access the Deployed Dashboard

After ECS deployment, find the dashboard URL.

If there is a load balancer:

```bash
aws elbv2 describe-load-balancers --region eu-west-2
```

Use the DNS name shown.

If running ECS Fargate without a load balancer:

```bash
aws ecs list-clusters --region eu-west-2
aws ecs list-services --cluster c23-ecs-cluster --region eu-west-2
aws ecs list-tasks --cluster c23-ecs-cluster --region eu-west-2
```

Then inspect the running task/network interface in the AWS Console to find the public IP.

The dashboard runs on:

```text
port 8501
```

---

## 12. Updating the Dashboard After Code Changes

If you only changed dashboard code:

```bash
cd infrastructure
bash dashboard.sh
```

This rebuilds the dashboard image, pushes it to ECR, and starts a new ECS deployment.

If ECS does not pick up the latest image, force deployment manually:

```bash
aws ecs update-service \
  --cluster c23-ecs-cluster \
  --service c23_travel_simulator_dashboard_service \
  --force-new-deployment \
  --region eu-west-2
```

---

## 13. Updating Terraform

If you changed infrastructure code:

```bash
cd infrastructure
terraform plan
terraform apply
```

If the change affects ECS task definitions or environment variables, update the ECS service after applying:

```bash
bash dashboard.sh
```

---

## 14. Testing

Run all tests from the repository root:

```bash
pytest
```

Run dashboard tests:

```bash
pytest dashboard/tests/
```

Run simulation tests:

```bash
pytest simulation/
```

Run TfL/network tests:

```bash
pytest tfl_data_and_network/tests/
```

---

## 15. Common Issues

### `gcloud command not found`

This happens when `ee.Authenticate()` is called inside ECS.

Fix:
- use `GOOGLE_APPLICATION_CREDENTIALS_JSON` in ECS
- initialise Earth Engine with service account credentials
- do not call `ee.Authenticate()` in deployed containers

### `AccessDeniedException` when invoking Lambda

The ECS task role does not have `lambda:InvokeFunction`.

Fix:
- add a policy allowing the dashboard ECS task role to invoke the simulation Lambda

### Dashboard shows old code after deployment

The image was pushed to ECR, but ECS has not started a new task.

Fix:

```bash
cd infrastructure
bash dashboard.sh
```

or:

```bash
aws ecs update-service \
  --cluster c23-ecs-cluster \
  --service c23_travel_simulator_dashboard_service \
  --force-new-deployment \
  --region eu-west-2
```

### `JSONDecodeError` for Google credentials

The value in `GOOGLE_APPLICATION_CREDENTIALS_JSON` is not valid JSON.

Fix:
- in ECS, use Secrets Manager
- locally, remove `GOOGLE_APPLICATION_CREDENTIALS_JSON` and use `earthengine authenticate`
- if using `.env`, the JSON must be one valid JSON string

### `No module named ...`

Run commands from the repository root unless the README says otherwise.

---

## 16. Cleanup

Destroy AWS infrastructure:

```bash
cd infrastructure
terraform destroy
```

Remove local Docker images if needed:

```bash
docker image ls
docker rmi <image-name>
```

---

## Security Notes

Never commit:
- `.env`
- `terraform.tfvars`
- Google service account JSON files
- OpenAI API keys
- AWS access keys
- private Terraform state files
- `.terraform/`

Recommended `.gitignore` entries:

```gitignore
.env
*.tfvars
.terraform/
terraform.tfstate
terraform.tfstate.backup
*.pem
*.json
```

Only commit non-secret example files such as:

```text
.env.example
```
