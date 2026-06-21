# Robotaksi Simülasyon - Takım Bumblebee

TEKNOFEST Robotaksi-Binek Otonom Araç Yarışması, Hazır Araç Kategorisi simülasyon çalışması.
ROS2 Foxy + Gazebo Classic, Docker içinde çalıştırılır.

**Önemli:** Her takım üyesi kendi laptop'unda kendi container'ını çalıştırır. Container'lar
birbirine ağ üzerinden bağlı DEĞİLDİR. Senkronizasyon git üzerinden yapılır — kod push/pull
edilir, ROS topic'leri laptop'lar arası paylaşılmaz.

---

## 1. İlk Kurulum (her laptop'ta bir kere)

```bash
git clone <REPO_URL> robotaksi_ws
cd robotaksi_ws
make build
```

`make build` Docker image'ini oluşturur. Birkaç dakika sürer, bir kere yapılır
(Dockerfile değişmediği sürece tekrar gerekmez).

## 2. Container'ı Başlatma

```bash
make run
```

Bu komut:
- Gazebo/RViz GUI'sinin laptop ekranında açılmasına izin verir (`xhost`)
- `robotaksi_ws/src` klasörünü container içine mount eder (container içinde
  yapılan değişiklikler laptop'taki dosyalarda da görünür, ve tam tersi)
- Container'a girip bash terminali açar

Aynı laptop'ta ikinci bir terminal açmak istersen (örneğin bir terminalde Gazebo
çalışırken başka birinde node başlatmak için):

```bash
make exec
```

## 3. Workspace'i Build Etme

Kod çektikten (`git pull`) sonra veya yeni dosya ekledikten sonra, **container
içindeyken**:

```bash
colcon build --symlink-install
source install/setup.bash
```

Veya container dışından (host terminalinden), container zaten çalışıyorsa:

```bash
make colcon
```

## 4. Çalışmayı Bitirme

```bash
make stop
```

---

## Günlük İş Akışı (ÖNEMLİ — laptop'lar birbirini görmüyor)

Her laptop kendi bağımsız container'ını çalıştırdığı için, entegrasyon **git
üzerinden** olur:

1. Çalışmaya başlamadan önce: `git pull`
2. `make colcon` ile yeni kodu build et
3. Kendi node'unu test et (gerekirse sahte/dummy topic ile, başkasının node'u
   olmadan çalışacak şekilde)
4. Küçük, sık commit'ler yap — büyük "her şeyi bitirince push ederim" bekleme
5. `git push`
6. **Belirlenen entegrasyon saatinde** (takımca konuşulan saat) hepiniz `git pull`
   yapıp aynı anda en güncel hali build edin; tüm sistemin BİR laptop'ta uçtan
   uca çalıştığını doğrulayın — final video o laptop'tan kaydedilecek.

## Klasör Yapısı

```
robotaksi_ws/
├── Makefile              <- docker build/run/exec/colcon kısayolları
├── docker/
│   └── Dockerfile
├── README.md
├── .gitignore
└── src/
    ├── robotaksi_world/          <- Kaptan: Gazebo dünyası + araç spawn
    ├── robotaksi_description/    <- Kaptan: BEE1 URDF (ölçüler + sensör konumları)
    ├── robotaksi_control/        <- Üye-5: waypoint controller + CAN bridge stub
    └── robotaksi_localization/   <- Üye-3: odometry relay (EKF placeholder)
```

## Topic Sözleşmesi (Kod yazmadan önce bunu değiştirmeyin)

| Topic | Tip | Sahibi |
|---|---|---|
| `/odom` | `nav_msgs/msg/Odometry` | Gazebo plugin → Üye-3 relay eder |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Üye-5 yayınlar |
| `/scan` | `sensor_msgs/msg/LaserScan` | Kaptan'ın lidar plugin'i |
| `/beemobs/*` (stub) | `can_bridge_stub.py` içinde tanımlı | Üye-5, `/cmd_vel`'den türetir |

Bir topic adını veya tipini değiştirmeniz gerekiyorsa, push etmeden önce takıma
haber verin — aksi halde başkasının node'u sessizce çalışmaz hale gelir.

## Sorun Giderme

- **Gazebo GUI açılmıyor / boş pencere:** `xhost +local:docker` komutunu host
  terminalinde (container dışında) tekrar çalıştırın.
- **`colcon build` hata veriyor:** Önce `rm -rf build install log` ile temiz
  build deneyin (mount edilen klasördeki eski build artifact'leri sorun
  çıkarabilir).
- **Container zaten çalışıyor hatası:** `make stop`, sonra tekrar `make run`.