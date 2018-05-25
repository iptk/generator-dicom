FROM python:3.6-alpine
RUN pip install pydicom requests
COPY generator.py /generator.py
CMD ["python3", "/generator.py"]