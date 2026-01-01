# Use a lightweight Python version
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Initialize the database (Run the creation script if needed, or rely on app.py)
# Note: Best practice is to handle DB creation in the app logic or a start script.

# Expose the port Flask runs on
EXPOSE 5000

# Command to run the app using Gunicorn (Production Server)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]