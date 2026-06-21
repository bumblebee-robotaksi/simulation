IMAGE_NAME := robotaksi_foxy
CONTAINER_NAME := robotaksi_dev
WORKSPACE := $(shell pwd)

.PHONY: build run exec stop clean colcon help

help:
	@echo "Kullanim (her laptop kendi container'ini calistirir):"
	@echo "  make build   -> Docker image'ini olusturur (ilk kurulumda veya Dockerfile degisince)"
	@echo "  make run     -> Container'i baslatir (Gazebo/RViz GUI acik, src/ mount edilmis)"
	@echo "  make exec    -> Calisan container'a YENI bir terminal acar (ayni laptop'ta 2. terminal)"
	@echo "  make colcon  -> Container ICINDE workspace'i build eder (kod cektikten sonra calistir)"
	@echo "  make stop    -> Calisan container'i durdurur"
	@echo "  make clean   -> Image'i ve dangling layer'lari siler"

build:
	docker build -t $(IMAGE_NAME) -f docker/Dockerfile .

run:
	xhost +local:docker
	docker run -it --rm \
		--name $(CONTAINER_NAME) \
		--network host \
		--env="DISPLAY=$(DISPLAY)" \
		--env="LIBGL_ALWAYS_SOFTWARE=1" \
		--volume="/mnt/wslg/.X11-unix:/tmp/.X11-unix:rw" \
		--volume="$(WORKSPACE):/robotaksi_ws" \
		$(IMAGE_NAME)

exec:
	docker exec -it $(CONTAINER_NAME) bash

colcon:
	docker exec -it $(CONTAINER_NAME) bash -c "cd /robotaksi_ws && colcon build --symlink-install && source install/setup.bash"

stop:
	docker stop $(CONTAINER_NAME)

clean:
	docker rmi $(IMAGE_NAME) || true
	docker image prune -f