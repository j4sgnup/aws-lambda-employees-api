# Employee CRUD API — AWS Lambda + FastAPI + DynamoDB

A serverless REST API built with **FastAPI**, deployed via **AWS SAM**, backed by **DynamoDB**.

## Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 |
| Framework | FastAPI + Mangum (ASGI adapter) |
| Infrastructure | AWS SAM (Lambda + API Gateway + DynamoDB) |
| Local dev | Docker + DynamoDB Local |

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/employees` | List all employees |
| `POST` | `/employees` | Create an employee |
| `GET` | `/employees/{id}` | Get employee by ID |
| `PATCH` | `/employees/{id}` | Partial update |
| `DELETE` | `/employees/{id}` | Delete employee |

## Local Development

### Prerequisites
- Docker
- AWS SAM CLI
- AWS CLI
- Python 3.12

### Setup

1. **Install layer dependencies inside Linux (required — SAM runs on Linux):**
    ```powershell
    docker run --rm -v "${PWD}/employees-api/layer":/layer -w /layer python:3.12-slim bash -c "pip install -r requirements.txt -t python/lib/python3.12/site-packages --upgrade"
    ```

2. **Start DynamoDB Local:**
    ```powershell
    docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -sharedDb
    ```

3. **Create the Employees table:**
    ```powershell
    aws dynamodb create-table --table-name Employees --attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH --billing-mode PAY_PER_REQUEST --endpoint-url http://localhost:8000 --region us-east-1
    ```

4. **Create `env.json`** (gitignored — do not commit):
    ```json
    {
      "EmployeesFunction": {
        "TABLE_NAME": "Employees",
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "dummy",
        "AWS_SECRET_ACCESS_KEY": "dummy",
        "DYNAMODB_ENDPOINT": "http://dynamodb-local:8000"
      }
    }
    ```

5. **Set up Docker network and build:**
    ```powershell
    docker network create sam-local
    docker network connect sam-local dynamodb-local
    sam build --template-file employees-api/template.yaml
    sam local start-api --template-file employees-api/template.yaml --env-vars env.json --docker-network sam-local --warm-containers EAGER
    ```

6. **Test** — open `employees-api/employees.http` in VS Code with the REST Client extension, or:
    ```powershell
    Invoke-RestMethod http://127.0.0.1:3000/employees
    ```

## Deploy to AWS

```powershell
aws configure
sam build --template-file employees-api/template.yaml
sam deploy --guided --template-file employees-api/template.yaml
```

## Run Tests

```powershell
cd employees-api
python -m pytest test_emp_api.py -q
```
