IMAGE_NAME := robotaksi_foxy
CONTAINER_NAME := robotaksi_dev
WORKSPACE := $(shell pwd)

.PHONY: build run exec stop clean colcon sim control check graph help

help:
	@echo "Kullanim (her laptop kendi container'ini calistirir):"
	@echo "  make build    -> Docker image'ini olusturur (ilk kurulumda veya Dockerfile degisince)"
	@echo "  make run      -> Container'i baslatir (Gazebo/RViz GUI acik, src/ mount edilmis)"
	@echo "  make exec     -> Calisan container'a YENI bir terminal acar (ayni laptop'ta 2. terminal)"
	@echo "  make colcon   -> Workspace'i build eder (kod cektikten sonra calistir)"
	@echo "  make sim      -> Build + Gazebo simulasyonunu baslatir (TEK KOMUT)"
	@echo "  make control  -> Build + waypoint controller'i baslatir (TEK KOMUT, sim ayri terminalde acik olmali)"
	@echo "  make check    -> Aktif Node ve Topic listesini gosterir (Text tabanli)"
	@echo "  make graph    -> ROS Agini gorsel olarak cizer (Baglantilari gormek icin HARIKA)"
	@echo "  make stop     -> Calisan container'i durdurur"
	@echo "  make clean    -> Image'i ve dangling layer'lari siler"

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
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install"

# TEK KOMUT: build + source + Gazebo'yu baslat (ayri terminalde, container zaten 'make run' ile acik olmali)
sim:
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install --packages-select robotaksi_world robotaksi_description && source install/setup.bash && ros2 launch robotaksi_world sim.launch.py"

# TEK KOMUT: build + source + waypoint controller'i baslat
control:
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install --packages-select robotaksi_control && source install/setup.bash && ros2 run robotaksi_control waypoint_controller"

# Hizli saglik kontrolu: Hangi node'lar ve topic'ler aktif?
check:
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && source /robotaksi_ws/install/setup.bash && echo '--- AKTIF NODE LAR ---' && ros2 node list && echo '' && echo '--- AKTIF TOPIC LER ---' && ros2 topic list -t"

# Gorsel Baglanti Haritasi
graph:
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && source /robotaksi_ws/install/setup.bash && rqt_graph"

stop:
	docker stop $(CONTAINER_NAME)

clean:
	docker rmi $(IMAGE_NAME) || true
	docker image prune -f