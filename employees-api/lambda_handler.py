from mangum import Mangum
from app import app

# Mangum adapts an ASGI app (FastAPI) to AWS Lambda + API Gateway/Lambda
# The exported `handler` is the function AWS Lambda will invoke.
handler = Mangum(app)
