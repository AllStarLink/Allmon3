# Adjust `allmon3.ini`
My asl host lives on 192.168.100.19, so my `allmon3.ini` looks like this:
```
[59913]
host=192.168.100.19
port=5038
user=admin
pass=llcgi
```

# Configure authentication
`docker run -it -v $PWD:/etc/allmon3 allmon3-app allmon3-passwd admin`

# Build images
`docker-compose build`

# Start containers
`docker-compose up`

