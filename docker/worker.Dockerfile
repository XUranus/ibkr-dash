FROM python:3.12-slim

WORKDIR /app

COPY ibkr_dash_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ibkr_dash_worker/ .

CMD ["python", "-m", "worker.main", "run-scheduler"]
