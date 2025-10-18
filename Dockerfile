# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app


# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create all required output directories
RUN mkdir -p "/root/OneDrive - Bunzl Continental Europe/Documents - Bonvig/Produktoprettelser" \
    "/root/OneDrive - Bunzl Continental Europe/Documents - Bonvig/Produktbilleder" \
    "/root/OneDrive - Bunzl Continental Europe/Documents - Bonvig/Produktbilleder_1500x1500" \
    /app/cache

# Install Chrome browser (modern key handling)
RUN apt-get update && \
    apt-get install -y wget gnupg && \
    wget -O /usr/share/keyrings/google-chrome.gpg https://dl-ssl.google.com/linux/linux_signing_key.pub && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*
# Copy your project code
COPY . .

# Default command to run your main scraper (update as needed)
CMD ["python", "csv_data_transformation/sanitering.py"]