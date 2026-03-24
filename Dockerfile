# Use a tiny, secure version of Python
FROM python:3.12-slim

# Create a place for the code
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your script and your .env (locally)
COPY . .

# Start the Sentry!
CMD ["python", "guard.py"]
