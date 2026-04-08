# AWS Lambda Employee CRUD - Steps
__Elevated Powershell (as admin)__
```
winget install -e --id Amazon.SAM-CLI
```


__Bash__
### Create folders

```cmd
mkdir -p employees-api/layer/python/lib/python3.12/site-packages

employees-api/app.py <<'PY'
```

```python
from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def read_root():
    return {'ok': True}
PY
```

```cmd
cat > employees-api/layer/requirements.txt <<'REQ'
```
```python
fastapi
mangum
pydantic
boto3
REQ

```

### Install dependencies
```python
pip install -r employees-api/layer/requirements.txt -t employees-api/layer/python/lib/python3.12/site-packages --upgrade
```

#### Pack dependencies in zip
From Bash
```cmd
cd employees-api/layer
zip -r layer.zip python
```
or from Poweshell
```
cd employees-api/layer
Compress-Archive -Path employees-api\layer\python\* -DestinationPath employees-api\layer\layer.zip -Force
``

Deploy using SAM CLI

```bash
sam build
sam deploy --guided
```

Verify Installation
```bash
sam --version
```
The following command will create the emplyee-api from scratch
```
sam init --no-input --runtime python3.12 --name employees-api
```

## Test in Local windows

__Test with PyTest__

1. Install packages locally, do not include in requirements.txt
    ```
    pip install pytest requests fastapi httpx boto3
    ```
1. Run the test using pytest (mocked dynamodb)
    ```
    cd employees-api
    pip install pytest requests fastapi httpx boto3
    python -m pytest test_emp_api.py -q
    ```
    To see exact cause run tests with output enabled:
    ```
    cd employees-api
    pytest -q -k test_create_employee -s
    ```


### Test with sam and docker in windows
__Prerequisites: sam-cli and docker__


1. Install layer deps into the layer 
    ```
    # use your Python from venv; run from repo root
    python -m pip install -r employees-api/layer/requirements.txt -t employees-api/layer/python/lib/python3.12/site-packages --upgrade
    ```

1. Start DynamoDB Local (Docker)
    ```
    docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -sharedDb
    ```
    > `-sharedDb` is required: without it DynamoDB Local stores separate tables per access key ID.
    > The Lambda uses `dummy` credentials; your AWS CLI may use different ones — `-sharedDb` ignores that.

1. Create the Employees table in the local DynamoDB

    AWS (requires aws cli installed)
    ```
    winget install -e --id Amazon.AWSCLI
    ```

    ```
    aws dynamodb create-table \
    --table-name Employees \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url http://localhost:8000
    ```

    AWS One line
    ```
    aws dynamodb create-table --table-name Employees --attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH --billing-mode PAY_PER_REQUEST --endpoint-url http://localhost:8000 --region us-east-1
    ```
    Check tables
    ```
    aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1
    ```

    Python command line (Bash)
    ```
    python - <<'PY'
    import boto3
    d = boto3.client('dynamodb', endpoint_url='http://localhost:8000', region_name='us-east-1',
                    aws_access_key_id='dummy', aws_secret_access_key='dummy')
    d.create_table(
    TableName='Employees',
    AttributeDefinitions=[{'AttributeName':'id','AttributeType':'S'}],
    KeySchema=[{'AttributeName':'id','KeyType':'HASH'}],
    BillingMode='PAY_PER_REQUEST'
    )
    print('table created')
    PY
    ```


1. Prepare an env-vars JSON for SAM local 

    It maps to the logical function name in the template)

    Create a file env.json with:

    ```json
    {
    "EmployeesFunction": {
        "TABLE_NAME": "Employees",
        "AWS_REGION": "us-east-1",
        "AWS_ACCESS_KEY_ID": "dummy",
        "AWS_SECRET_ACCESS_KEY": "dummy"
    }
    }
    ```
1. Start the API locally with SAM

    ```
    sam build --template-file employees-api/template.yaml
    sam local start-api --template-file employees-api/template.yaml --env-vars env.json

    docker network create sam-local

    docker network connect sam-local dynamodb-local
    ```
    Default local URL: http://127.0.0.1:3000

    __After build inspect the artifacts:__

    Function build dir:

    __.aws-sam/build/EmployeesFunction/__ (look for installed packages under a python/lib or site-packages location)

    Layer build dir:

    __.aws-sam/build/SharedLayer/__ or similar — open the layer zip or directory and confirm the packages are present (e.g. fastapi folder).

    If AWS CLI is installed, check the deploy details
    ```
    aws sts get-caller-identity
    aws configure list
    ```
    
### commands to run after any change to test in local windows

```
cd C:\Users\______\python\aws-lambda

docker stop /dynamodb-local
docker rm /dynamodb-local

docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -sharedDb

aws dynamodb create-table --table-name Employees --attribute-definitions AttributeName=id,AttributeType=S --key-schema AttributeName=id,KeyType=HASH --billing-mode PAY_PER_REQUEST --endpoint-url http://localhost:8000 --region us-east-1

# Verify table exists
aws dynamodb list-tables --endpoint-url http://localhost:8000 --region us-east-1

# Connect container to SAM network (must redo every restart)
docker network create sam-local
docker network connect sam-local dynamodb-local

sam build --template-file employees-api/template.yaml

sam local start-api --template-file employees-api/template.yaml --env-vars env.json --docker-network sam-local --warm-containers EAGER

docker network connect sam-local dynamodb-local
```

Test in local with CURL
```
# Create
curl -X POST http://127.0.0.1:3000/employees -H "Content-Type: application/json" -d "{\"name\":\"Alice\",\"role\":\"Engineer\",\"salary\":90000}"

# List
curl http://127.0.0.1:3000/employees
```

Or use the REST Client VS Code extension — open `employees-api/employees.http` and click `Send Request`.

## Git — Push to Remote Repo

1. Create a new empty repo on GitHub (do NOT initialize with README)

1. Initialize and push:
    ```powershell
    cd C:\Users\webso\python\aws-lambda

    git init
    git add .
    git status          # verify env.json and env/ are NOT listed
    git commit -m "Initial commit: Employee CRUD API with FastAPI + SAM + DynamoDB"

    git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO-NAME.git
    git branch -M main
    git push -u origin main
    ```

> `env.json` is gitignored — it contains local credentials. Recreate it manually after cloning.

## Deploy to AWS

1. Configure real AWS credentials:
    ```powershell
    aws configure
    ```

1. Build and deploy:
    ```powershell
    sam build --template-file employees-api/template.yaml
    sam deploy --guided --template-file employees-api/template.yaml
    ```
    `--guided` will prompt for stack name, AWS region, S3 bucket (auto-created), and confirm IAM changes.
    Settings are saved to `samconfig.toml` — subsequent deploys just need:
    ```powershell
    sam deploy --template-file employees-api/template.yaml
    ```

1. After deploy, get the live API URL from the output:
    ```
    Outputs: ApiUrl = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/Prod/
    ```

---

## Errors Encountered and How They Were Fixed

### 1. `Runtime.ImportModuleError: No module named 'pydantic_core._pydantic_core'`

**What happened:**
When SAM local invoked the Lambda, it immediately crashed with this error before any request code ran.

**Why it happened:**
The layer dependencies (`fastapi`, `pydantic`, etc.) were installed on Windows using:
```powershell
pip install -r employees-api/layer/requirements.txt -t employees-api/layer/python/lib/python3.12/site-packages
```
`pydantic` (v2+) contains `pydantic_core`, which is a compiled native extension written in Rust. When pip installs it on Windows, it downloads and unpacks a **Windows `.whl` (wheel)** — a binary built specifically for Windows x86_64. This binary contains `.pyd` files (Windows DLLs).

SAM local runs your Lambda inside a **Linux Docker container** (the official AWS Lambda runtime image). When the container tries to import `pydantic_core`, it finds the Windows `.pyd` binary and cannot load it — Windows DLLs don't run on Linux.

The error `No module named 'pydantic_core._pydantic_core'` is Python's way of saying: "I found the package folder but the compiled extension inside it is not loadable on this OS."

**The fix:**
Rebuild the layer dependencies **inside a Linux Docker container** so pip downloads the Linux wheel instead:
```powershell
# From repo root — runs pip inside a Linux Python 3.12 container
docker run --rm -v "${PWD}/employees-api/layer":/layer -w /layer python:3.12-slim bash -c "pip install -r requirements.txt -t python/lib/python3.12/site-packages --upgrade"
```
This replaces the Windows `.pyd` files with Linux `.so` shared libraries that the Lambda container can load.

Alternatively: build using WSL (Ubuntu), which is also Linux.

---

### 2. `Function timed out after 3 seconds`

**What happened:**
SAM reported a 3-second timeout with no response from the container.

**Why it happened:**
The default Lambda timeout in `template.yaml` was 3 seconds. During the first invoke, the container had to cold-start (pull image, initialize Python, import FastAPI + pydantic), which took longer than 3 seconds. With no response, SAM killed the container.

**The fix:**
Increased `Timeout` to 30 seconds in `template.yaml` to allow full startup during local development:
```yaml
EmployeesFunction:
  Properties:
    Timeout: 30
```

---

### 3. `ResourceNotFoundException: Requested resource not found` (DynamoDB table)

**What happened:**
The Lambda started successfully but every API call returned a 500 with `ResourceNotFoundException`.

**Why it happened — Part A: Networking**
DynamoDB Local runs as a Docker container on `localhost:8000`. The Lambda also runs in a Docker container. Containers are isolated — `localhost` inside the Lambda container refers to the Lambda container itself, not the host machine. So `http://localhost:8000` was unreachable.

**Fix A:** Create a shared Docker network and start SAM with `--docker-network`:
```powershell
docker network create sam-local
docker network connect sam-local dynamodb-local
sam local start-api ... --docker-network sam-local
```
This lets the Lambda container resolve `dynamodb-local` (the container name) as a hostname over the shared network.

**Why it happened — Part B: Per-credential namespacing**
DynamoDB Local (without `-sharedDb`) stores a **separate table namespace per `AWS_ACCESS_KEY_ID`**. The AWS CLI on the host had real AWS credentials, so the `Employees` table was created under those credentials. But the Lambda used `AWS_ACCESS_KEY_ID=dummy` (from `env.json`), so it looked in a completely different namespace and found nothing.

**Fix B:** Restart DynamoDB Local with `-sharedDb` so all clients share one table space regardless of credentials:
```powershell
docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local -jar DynamoDBLocal.jar -sharedDb
```

---

### 4. `DYNAMODB_ENDPOINT=None` — env.json value silently ignored

**What happened:**
Debug logs showed `DYNAMODB_ENDPOINT=None` even though `env.json` had `"DYNAMODB_ENDPOINT": "http://dynamodb-local:8000"`.

**Why it happened:**
SAM local's `--env-vars` only injects values for environment variables that are **already declared** in the `template.yaml` `Environment.Variables` block. Variables present in `env.json` but absent from the template are silently dropped. `DYNAMODB_ENDPOINT` was missing from the template.

**The fix:**
Added `DYNAMODB_ENDPOINT` to `template.yaml` with an empty string as the production default:
```yaml
Environment:
  Variables:
    TABLE_NAME: !Ref EmployeesTable
    DYNAMODB_ENDPOINT: ""   # overridden by env.json in local dev; empty = real AWS in prod
```
Now SAM passes the `env.json` value through to the container.

---

### 5. `TypeError: Float types are not supported. Use Decimal types instead`

**What happened:**
Creating an employee with a `salary` field (a float) threw a `TypeError` inside boto3.

**Why it happened:**
DynamoDB's Python SDK does not accept Python `float` values — it requires `decimal.Decimal`. This is because JSON floats can lose precision in IEEE 754 representation, and DynamoDB enforces exact numeric storage.

**The fix:**
Added a helper to convert floats to `Decimal` before writing to DynamoDB:
```python
from decimal import Decimal

def _floats_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    return obj

# Usage:
table.put_item(Item=_floats_to_decimal(item))
```
`str(obj)` is used (not `Decimal(obj)`) to avoid IEEE 754 floating point precision issues.

---

### 6. `ValidationException: Attribute name is a reserved keyword: role`

**What happened:**
The PATCH (update) endpoint threw a `ValidationException` from DynamoDB.

**Why it happened:**
DynamoDB has a list of [reserved keywords](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html) that cannot be used directly in expressions. `role` is one of them. Writing `SET role = :r` in an `UpdateExpression` causes DynamoDB to reject the request.

**The fix:**
Use `ExpressionAttributeNames` to alias every attribute name with a `#` placeholder:
```python
expr_names = {'#r': 'role', '#n': 'name', '#s': 'salary'}
update_expression = 'SET #n = :n, #r = :r, #s = :s'
table.update_item(
    Key={'id': id},
    UpdateExpression=update_expression,
    ExpressionAttributeValues=expr_vals,
    ExpressionAttributeNames=expr_names,
    ReturnValues='ALL_NEW',
)
```

---

### 7. PUT vs PATCH — wrong HTTP method for partial update

**What happened:**
The update endpoint was defined as `PUT` but only updated the fields provided (partial update behavior).

**Why it matters:**
By REST convention:
- `PUT` = full replacement — the client sends the complete resource; missing fields are deleted
- `PATCH` = partial update — only the provided fields are changed

The implementation was PATCH behavior exposed as PUT, which is misleading and incorrect.

**The fix:**
Changed `@app.put` to `@app.patch` in `app.py` and updated `employees.http` accordingly.








