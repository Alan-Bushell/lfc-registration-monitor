FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and system dependencies
# We only need Chromium for this bot
RUN playwright install --with-deps chromium

# Copy the rest of the application code
COPY . .

# Run the application
# Ensure you pass the TARGET_CALENDAR_ID environment variable when running
# e.g., docker run -e TARGET_CALENDAR_ID=your@email.com ...
CMD ["python", "main.py"]
