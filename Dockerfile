FROM python:3.11-slim

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml requirements.txt ./

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Copy source code
COPY src/ ./src/

# Set working directory
WORKDIR /app/src

# Expose port
EXPOSE 8501

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
