FROM python:3.9-slim

# Add sqlite3 tools
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Create data directory for persistent storage and set proper permissions
RUN mkdir -p /data && chmod 777 /data

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Define environment variable
ENV DISCORD_TOKEN apa
ENV NOTIFY_CHANNEL_ID boll

# Run script.py when the container launches
CMD ["python", "script.py"]