FROM python:3.11-slim

# Install rq-dashboard (latest version compatible with RQ 2.x)
RUN pip install --no-cache-dir rq-dashboard

# Expose port
EXPOSE 9181

# Set environment variables
ENV RQ_DASHBOARD_REDIS_URL=redis://redis:6379/0

# Run rq-dashboard
CMD ["rq-dashboard", "--bind", "0.0.0.0", "--port", "9181"]
