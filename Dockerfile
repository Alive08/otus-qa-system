FROM python:3.10-slim

WORKDIR /opt/echo-http

COPY echo_http.py .

EXPOSE 9000

ENTRYPOINT ["python3", "echo_http.py"]
