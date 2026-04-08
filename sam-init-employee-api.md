# AWS SAM — Init & Deploy guide for Employees API

This document collects safe, repeatable instructions for initializing, building and deploying the Employees API (FastAPI + Mangum) and a Lambda Layer.

Prerequisites
- Install the AWS SAM CLI (MSI, `winget`, `choco`, or Homebrew). Verify with `sam --version`.
- Install Docker Desktop (required for `sam local` and for building native wheels).
- Install and configure the AWS CLI (`aws configure`) or ensure credentials are available via environment/profile.

Safe `sam init` guidance
- `sam init` scaffolds a new SAM project. Avoid running `sam init` inside a non-empty project directory (it can overwrite files).
- Recommended: run `sam init` so it creates its own directory. Example (non-interactive):

```
sam init --no-input --runtime python3.12 --app-template hello-world --name employees-sam
```

- If you already have a `template.yaml` (like this repo's `employees-api/template.yaml`), you do NOT need `sam init`. You can use `sam build` and `sam deploy` directly against your template.

Install SAM CLI (Windows examples)
- MSI: Download latest release from the SAM releases page and run the installer.
- winget (admin PowerShell):

```
winget install --id Amazon.AWS.SAMCLI -e
```

- Chocolatey (admin PowerShell): `choco install aws-sam-cli`

Build & deploy existing SAM template (recommended if you already edited `template.yaml`)
- Build using the template in the repository (no `cd` required):

```
sam build --template-file employees-api/template.yaml
```

- Deploy (guided):

```
sam deploy --guided --template-file employees-api/template.yaml --stack-name employees-sam
```

Notes about layers and native dependencies
- If your layer includes only pure-Python packages, you can install them with `pip` directly into the layer target path. Example (no `cd`):

```
python -m pip install -r employees-api/layer/requirements.txt -t employees-api/layer/python/lib/python3.12/site-packages --upgrade
```

- If any dependency has compiled extensions, build the layer in an Amazon Linux environment (Docker). Example — replace `<FULL_PATH_TO_PROJECT>` with the absolute path to the project root on your machine:

```
docker run --rm -v <FULL_PATH_TO_PROJECT>:/var/task -w /var/task public.ecr.aws/lambda/python:3.12 \
  pip install -r employees-api/layer/requirements.txt -t employees-api/layer/python/lib/python3.12/site-packages
```

- Zip the layer (PowerShell):

```
Compress-Archive -Path employees-api/layer/python/* -DestinationPath employees-api/layer/layer.zip
```

Alternative zip (Linux/macOS):

```
zip -r employees-api/layer/layer.zip employees-api/layer/python
```

Notes about `TABLE_NAME` and DynamoDB
- The SAM template in this repo creates a DynamoDB table and injects its name into the Lambda function environment as `TABLE_NAME` (no manual action required when deploying with the template).
- If you create the DynamoDB table manually in the AWS Console, set the Lambda environment variable `TABLE_NAME` to the exact table name in the Lambda configuration (or update the SAM template to reference your table name).

Recommended deploy workflow (using this repo's template)
1. Ensure AWS credentials are configured (`aws configure` or environment/profile credentials).
2. Build the project with `sam build --template-file employees-api/template.yaml`.
3. Deploy with `sam deploy --guided --template-file employees-api/template.yaml --stack-name employees-sam` and follow prompts.
4. After deploy, SAM prints the API URL. Use it to test the endpoints (the FastAPI app is adapted by Mangum — the Lambda handler is `lambda_handler.handler`).

Local testing
- Use `sam local start-api --template employees-api/template.yaml` to run the API locally (requires Docker). Then invoke endpoints at the printed localhost URL.

Recovery if you accidentally ran `sam init` in a non-empty folder
- If you use Git, run `git status` and `git restore`/`git checkout` or reset to the previous commit.
- If no VCS, restore from backup or re-create files from this repository's copies.

Further reading
- AWS SAM CLI docs: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html
- SAM CLI GitHub releases: https://github.com/aws/aws-sam-cli/releases
