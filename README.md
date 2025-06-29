# postgresql-concurrency-stress-test
postgresql-concurrency-stress-test


### how to run 
```
# run postgresql container from project root
docker-compuse up

# run fastapi server from project root
uvicorn app.main:app
gunicorn app.main:app -w 6 -k uvicorn.workers.UvicornWorker

# run locust from project root
locust -f script/locustfile.py -H http://localhost:8000
```

