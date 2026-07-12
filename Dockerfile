# Hugging Face Spaces (Docker SDK) image for the Autumn PM interview assistant.
# Pure standard library, so no requirements.txt is needed.
FROM python:3.12-slim

# Spaces run the container as UID 1000; create that user to avoid permission issues.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    APP_DATA_DIR=/home/user/app/data

WORKDIR /home/user

COPY --chown=user . .

# Spaces route public traffic to app_port (7860 by default).
EXPOSE 7860

CMD ["python3", "-B", "app/web_app.py", "--host", "0.0.0.0", "--port", "7860"]
