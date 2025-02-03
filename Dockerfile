# Use an official Python runtime as a parent image.
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create and set the working directory.
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files.
COPY . .

# Expose ports if needed (e.g., 8501 for Streamlit)
EXPOSE 8501

# Default command (adjust as needed, e.g., running your main Python service)
CMD ["python", "integration.py"]
