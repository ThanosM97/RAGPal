# Use an official Python runtime as a parent image
FROM python:3.9

# Set the working directory in the container
WORKDIR /RAGPal

# Copy the current directory contents into the container at /RAGPal
COPY . /RAGPal

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 5000 available to the world outside this container
EXPOSE 5000

# # Set environmental variables
# ENV OPENAI_API_KEY=<YOUR_API_KEY>
# ENV OPENAI_API_BASE=<API_ENDPOINT>

# Run app.py when the container launches
CMD ["python", "app.py"]
