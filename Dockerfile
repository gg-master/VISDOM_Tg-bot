FROM python:3.9-slim

WORKDIR /PYTHON_APPS

RUN pip install cryptography

RUN addgroup --system docker
RUN adduser --system --group docker
RUN chown -R docker /PYTHON_APPS
USER docker

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . /PYTHON_APPS

ENTRYPOINT ["python", "main.py"]
