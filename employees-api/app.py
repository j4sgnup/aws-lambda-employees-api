from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List
import uuid
from decimal import Decimal


def _floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    return obj

# employees-api/app.py
# Simple FastAPI application exposing CRUD endpoints for an `Employees`
# DynamoDB table. The Lambda entrypoint is expected to use Mangum (see
# lambda_handler.py). The table name is read from `TABLE_NAME` env var so
# the same code works both locally and in Lambda/SAM deployments.

TABLE_NAME = os.environ.get('TABLE_NAME', 'Employees')

# Support a local DynamoDB endpoint for `sam local`/DynamoDB Local testing.
# When running in Docker (SAM local), use host.docker.internal to reach the
# host machine's Docker-exposed ports. In production the env var should be
# unset so boto3 uses normal AWS endpoints.
_ddb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
if _ddb_endpoint:
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url=_ddb_endpoint,
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    )
else:
    # Default behavior for production / when no local endpoint is provided
    dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table(TABLE_NAME)

# Request response schema
class Employee(BaseModel):
    # Full Employee model used for creating items and for responses.
    # `id` is optional and defaults to None so creating a new employee
    # without an explicit `id` does not trigger a validation error.
    id: Optional[str] = None
    name: str
    role: Optional[str] = None
    salary: Optional[float] = None


class UpdateEmployee(BaseModel):
    # Update model — all fields optional so partial updates won't trigger
    # request validation errors (422). This was added because the PUT
    # endpoint accepts partial payloads (e.g., only `salary`).
    name: Optional[str] = None
    role: Optional[str] = None
    salary: Optional[float] = None


class CreateEmployee(BaseModel):
    # Model for create requests: only require the minimal input from clients.
    name: str
    role: Optional[str] = None
    salary: Optional[float] = None


app = FastAPI()


@app.post('/employees', status_code=201)
def create_employee(emp: CreateEmployee, response: Response):
    # Create API should accept only the fields the client must provide.
    # The server generates the `id` to guarantee uniqueness and authority.
    emp_id = str(uuid.uuid4())
    # Use model_dump() to convert request model to dict
    item = emp.model_dump()
    item['id'] = emp_id
    try:
        table.put_item(Item=_floats_to_decimal(item))
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Per REST conventions, provide the location of the newly created
    # resource in the `Location` header so clients can follow it.
    response.headers['Location'] = f'/employees/{emp_id}'
    return item



@app.get('/employees/{id}')
def get_employee(id: str):
    try:
        resp = table.get_item(Key={'id': id})
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    item = resp.get('Item')
    if not item:
        raise HTTPException(status_code=404, detail='Not found')
    return item


@app.get('/employees')
def list_employees():
    # Note: `scan()` reads the entire table and is suitable only for
    # small datasets or admin/debug endpoints. For production and larger
    # datasets, prefer `query()` against a primary key or a Global
    # Secondary Index (GSI).
    #
    # Example: if you create a GSI on the `role` attribute called
    # `role-index`, you can query all employees with role='Engineer':
    #
    # from boto3.dynamodb.conditions import Key
    # resp = table.query(
    #     IndexName='role-index',
    #     KeyConditionExpression=Key('role').eq('Engineer')
    # )
    # items = resp.get('Items', [])
    #
    # Also consider using pagination (`LastEvaluatedKey`) and
    # ProjectionExpression to limit returned attributes.
    try:
        resp = table.scan()
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return resp.get('Items', [])


@app.patch('/employees/{id}')
def update_employee(id: str, emp: UpdateEmployee):
    update_parts = []
    expr_vals = {}
    expr_names = {}
    if emp.name is not None:
        update_parts.append('#n = :n')
        expr_vals[':n'] = emp.name
        expr_names['#n'] = 'name'
    if emp.role is not None:
        update_parts.append('#r = :r')
        expr_vals[':r'] = emp.role
        expr_names['#r'] = 'role'
    if emp.salary is not None:
        update_parts.append('#s = :s')
        expr_vals[':s'] = Decimal(str(emp.salary))
        expr_names['#s'] = 'salary'
    if not update_parts:
        raise HTTPException(status_code=400, detail='No fields to update')
    ue = 'SET ' + ', '.join(update_parts)
    try:
        resp = table.update_item(
            Key={'id': id},
            UpdateExpression=ue,
            ExpressionAttributeValues=expr_vals,
            ExpressionAttributeNames=expr_names,
            ReturnValues='ALL_NEW',
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return resp.get('Attributes')


@app.delete('/employees/{id}', status_code=204)
def delete_employee(id: str):
    try:
        table.delete_item(Key={'id': id})
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return None

