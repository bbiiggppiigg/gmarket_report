sudo uwsgi --http localhost:8080 --http-websockets --processes 8 --enable-threads  --master  --worker-reload-mercy 1200 --wsgi server:app
