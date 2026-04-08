from fastapi.testclient import TestClient
import pytest


class MockTable:
    def __init__(self):
        self.store = {}

    def put_item(self, Item):
        self.store[Item['id']] = Item
        return {}

    def get_item(self, Key):
        item = self.store.get(Key['id'])
        if item:
            return {'Item': item}
        return {}

    def scan(self):
        return {'Items': list(self.store.values())}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues, ReturnValues=None):
        item = self.store.get(Key['id'])
        if not item:
            # mimic boto3 behaviour: return no Attributes
            return {}
        # UpdateExpression expected like: 'SET name = :n, role = :r'
        expr = UpdateExpression.strip()
        if expr.upper().startswith('SET '):
            assignments = expr[4:].split(',')
            for a in assignments:
                left, right = a.split('=')
                field = left.strip()
                val_key = right.strip()
                if val_key in ExpressionAttributeValues:
                    item[field] = ExpressionAttributeValues[val_key]
        self.store[Key['id']] = item
        return {'Attributes': item}

    def delete_item(self, Key):
        self.store.pop(Key['id'], None)
        return {}

""" 
----What is a Pytest Fixture?
A fixture is a function designed to provide a fixed baseline or "setup" for your tests. 
Instead of repeating the same initialization code (like connecting to a database or creating a 
client) in every single test, you define it once in a fixture.

Key Characteristics:
Reusability: Multiple test functions can use the same fixture.

Dependency Injection: You don't "call" a fixture like a normal function; you list its name as 
an argument in your test function, and pytest injects the result for you.

Lifecycle Management: Fixtures can handle "teardown" (cleaning up after a test) using the 
yield keyword.

In your example:
The client fixture sets up your application and a mock database. When you write a test 
like def test_homepage(client):, pytest runs the fixture first and hands the resulting client object to your test.

----What is Monkeypatch?
Monkeypatching is the process of replacing or modifying an object, function, or attribute 
at runtime. In testing, it is used to swap out real components (that might be slow, expensive, or unpredictable) with "fake" versions.

Why use it?
Isolation: To test your code without actually hitting a live API or a real database.

Control: To force a function to return a specific value (e.g., making a "current_time" 
function always return "12:00 PM").

Safety: The monkeypatch fixture in pytest automatically restores everything to its 
original state after the test is finished, preventing "pollution" where one test breaks others.

In your example:
The line def client(monkeypatch): tells pytest to provide the built-in monkeypatch tool. 
You are using it to effectively "intercept" the application's environment and replace the real DynamoDB table with MockTable().
"""
@pytest.fixture
def client(monkeypatch):
    # Create an in-memory mock table
    mock = MockTable()

    # Monkeypatch boto3.resource so importing app does NOT attempt real AWS access.
    import boto3

    class DummyResource:
        def __init__(self, table):
            self._table = table

        def Table(self, name):
            return self._table

    monkeypatch.setattr(boto3, 'resource', lambda *args, **kwargs: DummyResource(mock))

    # Now import the application; it will use the patched boto3.resource
    import app as app_module

    client = TestClient(app_module.app)
    return client


def test_create_employee(client):
    resp = client.post('/employees', json={'name': 'Alice', 'role': 'Engineer', 'salary': 90000})
    assert resp.status_code == 201
    body = resp.json()
    assert body['name'] == 'Alice'
    assert 'id' in body


def test_get_employee_and_not_found(client):
    # create and use returned id
    resp = client.post('/employees', json={'name': 'Bob'})
    assert resp.status_code == 201
    body = resp.json()
    emp_id = body['id']

    # get existing
    resp2 = client.get(f'/employees/{emp_id}')
    assert resp2.status_code == 200
    assert resp2.json()['name'] == 'Bob'

    # get missing
    resp3 = client.get('/employees/missing-id')
    assert resp3.status_code == 404


def test_list_employees(client):
    r1 = client.post('/employees', json={'name': 'A'})
    r2 = client.post('/employees', json={'name': 'B'})
    assert r1.status_code == 201 and r2.status_code == 201
    id1 = r1.json()['id']
    id2 = r2.json()['id']

    resp = client.get('/employees')
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert any(i.get('id') == id1 for i in items)
    assert any(i.get('id') == id2 for i in items)


def test_update_employee(client):
    r = client.post('/employees', json={'name': 'Old', 'role': 'TBD'})
    assert r.status_code == 201
    emp_id = r.json()['id']

    resp = client.put(f'/employees/{emp_id}', json={'name': 'New', 'salary': 5000})
    assert resp.status_code == 200
    body = resp.json()
    assert body['name'] == 'New'
    assert body['salary'] == 5000


def test_delete_employee(client):
    r = client.post('/employees', json={'name': 'ToDelete'})
    assert r.status_code == 201
    emp_id = r.json()['id']

    resp = client.delete(f'/employees/{emp_id}')
    assert resp.status_code == 204
    # now missing
    resp2 = client.get(f'/employees/{emp_id}')
    assert resp2.status_code == 404
