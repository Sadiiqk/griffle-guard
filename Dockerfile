# 1. Get a lightweight Python computer
FROM python:3.12-slim

# 2. Create a folder inside the container called /app
WORKDIR /app

# 3. Copy our ingredients list and install the tools
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy our actual script into the container
COPY guard.py .

# 5. Tell the container what to do when it turns on
CMD ["python3", "guard.py"]
