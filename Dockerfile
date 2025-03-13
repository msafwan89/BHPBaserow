# Use the official Baserow Docker image
ARG FROM_IMAGE=baserow/baserow:latest
FROM $FROM_IMAGE as image_base

# Set working directory
WORKDIR /baserow

# Expose the correct port
EXPOSE 10000

# Default command to start Baserow
CMD ["bash", "-c", "baserow backend run"]
