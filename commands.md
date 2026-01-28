## TO CREATE CONTAINER FROM AN IMAGE
docker run -d --name faulty-worker   --network media-net   --add-host=host.docker.internal:host-gateway   -v media-storage:/app/uploads   -e REDIS_HOST=ebcce306b2bd   faultyworkerimage
