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
	@echo "  make plan     -> Build + A* rota planlayiciyi baslatir (TEK KOMUT)"
	@echo "  make stack    -> Sim + Planlayici + Kontrolcuyu sirayla tek seferde kaldirir (GOD MODE)"
	@echo "  make perceive  -> Build + YOLO/LiDAR Algi Node'unu baslatir"
	@echo "  make bumblebee -> Sim + Algi + Planlayici + Kontrolcuyu sirayla tek seferde kaldirir"
	@echo "  make nuke      -> Arkaplanda kalan tum ROS ve Gazebo process'lerini temizler"


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

# TEK KOMUT: build + source + A* Rota Planlayiciyi baslat
plan:
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install --packages-select robotaksi_planning && source install/setup.bash && ros2 run robotaksi_planning planner_node"

# MASTER KOMUT: Tum yigini (Simulasyon, Planlayici, Kontrolcu) tek seferde arkaplanda kaldirir
stack:
	@echo ">>> Onceki oturum temizleniyor..."
	-@docker exec $(CONTAINER_NAME) bash -c "pkill -9 -f ros2; pkill -9 -f gzserver; pkill -9 -f gzclient; sleep 2"
	@echo ">>> 1/3: Gazebo Simulasyonu baslatiliyor..."
	@docker exec -d $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install --packages-select robotaksi_world robotaksi_description && source install/setup.bash && ros2 launch robotaksi_world sim.launch.py"
	@sleep 7
	@echo ">>> 2/3: A* Rota Planlayici arkaplanda baslatiliyor..."
	@docker exec -d $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 run robotaksi_planning planner_node"
	@sleep 2
	@echo ">>> 3/3: Waypoint Kontrolcu terminale baglanarak baslatiliyor..."
	@docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 run robotaksi_control waypoint_controller"

# TEK KOMUT: build + source + YOLO/LiDAR Algi Node'unu baslat
perceive:
	@echo ">>> Bumblebee Algı Sistemi (YOLOv8 + LiDAR) Başlatılıyor..."
	docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && colcon build --symlink-install --packages-select robotaksi_perception && source install/setup.bash && ros2 run robotaksi_perception inference_node"

bumblebee:
	@echo ">>> Onceki oturum temizleniyor..."
	-@docker exec $(CONTAINER_NAME) bash -c "pkill -9 -f ros2; pkill -9 -f gzserver; pkill -9 -f gzclient; sleep 2"
	@echo ">>> [1/4] Gazebo Evreni baslatiliyor..."
	@docker exec -d $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 launch robotaksi_world sim.launch.py"
	@echo "          (Gazebo ve sensor topic'leri icin 10 saniye bekleniyor...)"
	@sleep 10
	@echo ">>> [2/4] Bumblebee Algi Beyni arkaplanda uyaniyor..."
	@docker exec -d $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 run robotaksi_perception inference_node"
	@sleep 4
	@echo ">>> [3/4] A* Planlayici haritayi yayinliyor..."
	@docker exec -d $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 run robotaksi_planning planner_node"
	@sleep 2
	@echo ">>> [4/4] Waypoint Kontrolcu aktif! Arac hareket ediyor."
	@docker exec -it $(CONTAINER_NAME) bash -c "source /opt/ros/foxy/setup.bash && cd /robotaksi_ws && source install/setup.bash && ros2 run robotaksi_control waypoint_controller"

nuke:
	@echo ">>> Sistem temizleniyor..."
	-@docker exec -it $(CONTAINER_NAME) bash -c "pkill -9 -f ros2; pkill -9 -f gzserver; pkill -9 -f gzclient"
	@echo ">>> Butun arkaplan ROS dugumlari temizlendi."