# Use an official Python runtime as a parent image
FROM python:3.8.19-slim

# Set environment variables
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libproj-dev \
    libpq-dev \
    libgeos-dev \
    gdal-bin \
    libgdal-dev \
    git \
    && apt-get clean

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install numpy before other dependencies
RUN pip install numpy

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Set the working directory
WORKDIR /app

# Copy the project files into the container
COPY . .

# Command to run the application
CMD ["gunicorn", "MeningitisPredictionProject.wsgi:application", "--bind", "0.0.0.0:8000"]
