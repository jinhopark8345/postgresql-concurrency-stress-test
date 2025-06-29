# postgresql-concurrency-stress-test
postgresql-concurrency-stress-test


### how to run 
```
# run postgresql service (container) from project root
docker-compuse up

# run redis service
docker run -d --name redis -p 6379:6379 redis:7-alpine

# run fastapi server from project root
# uvicorn app.main:app
ulimit -n 65535 # resolve 
gunicorn app.main:app -w 8 -k uvicorn.workers.UvicornWorker

# run locust from project root
locust -f script/locustfile.py -H http://localhost:8000
```

