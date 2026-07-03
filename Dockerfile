# Use the official lightweight Python image from Docker Hub
FROM python:3.11-slim

# Ensure log messages immediately appear in Cloud Run logs
ENV PYTHONUNBUFFERED=True

# Set the working directory inside the container
ENV APP_HOME=/app
WORKDIR $APP_HOME

# Copy all local files into the container
COPY . ./

# Install required packages (e.g., shiny, pandas, scikit-learn)
# This requires a requirements.txt file in your repository
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Cloud Run expects traffic on
EXPOSE 8080

# Command to run the application on container startup
# This example uses Shiny for Python's run command
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8080", "app.py"]
