# Use lightweight Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files (Zero third-party dependencies required)
COPY . /app

# Set PYTHONPATH environment variable to include src/
ENV PYTHONPATH=/app/src

# Expose Web Studio port (8080) and TCP Server port (9000)
EXPOSE 8080 9000

# Create volume mount point for persistent database disk storage
VOLUME ["/app/data"]

# Default command: Start Web Management Studio listening on 0.0.0.0:8080
CMD ["python3", "-m", "minidb.web", "--host", "0.0.0.0", "--port", "8080", "--data-dir", "/app/data"]
