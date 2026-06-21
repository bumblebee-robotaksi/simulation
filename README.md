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

## 3. Workspace'i Build Etme ve Çalıştırma

Kod çektikten (`git pull`) sonra veya yeni dosya ekledikten sonra, **host
terminalinden** (container `make run` ile zaten açık olmalı):

```bash
make colcon          # sadece build et, hicbir sey baslatma
make sim             # build + Gazebo simulasyonunu baslat (TEK KOMUT)
make control         # build + waypoint controller'i baslat (TEK KOMUT, ayri terminalde)
make check           # hizli saglik kontrolu: aktif topic listesini gosterir
```

`make sim` ve `make control` otomatik olarak build edip source'lar — artik
`colcon build && source install/setup.bash && ros2 launch ...` yazmaniza
gerek yok.

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
├── Makefile              <- docker build/run/exec/colcon/sim/control kisayollari
├── docker/
│   └── Dockerfile
├── README.md
├── .gitignore
└── src/
    ├── robotaksi_world/          <- Kaptan: Gazebo dunyasi, parkur geometrisi, engeller
    ├── robotaksi_description/    <- Uye-5: BEE1 URDF (gercek olculer + gorsel model)
    ├── robotaksi_control/        <- Uye-5: waypoint controller + CAN bridge stub
    ├── robotaksi_localization/   <- Uye-3: odometry relay (EKF placeholder)
    └── robotaksi_planning/       <- Uye-4: statik engel sakinma mantigi (YENI, henuz olusturulmadi)
```

`robotaksi_planning` henuz olusturulmadi. Uye-4 su komutla baslatabilir:

```bash
ros2 pkg create --build-type ament_python robotaksi_planning --dependencies rclpy sensor_msgs std_msgs
```

## Gece Görev Dağılımı

| Kişi | Görev | Bağımlılık |
|---|---|---|
| Kaptan | Parkur geometrisini gerçek yarışma pistine yaklaştır, 2. görev noktası ekle, en az 1 statik engel ekle | Yok, bağımsız |
| Üye-5 | BEE1 görsel modelini iyileştir, `can_bridge_stub.py` yaz, waypoint listesini güncelle | Kaptan'ın parkur koordinatları (son adım için) |
| Üye-3 | `odom_relay_node.py` yaz (`/odom` → `/robotaksi/odom`) | Yok, sahte/dummy `/odom` ile bağımsız test edilebilir |
| Üye-4 | `robotaksi_planning` paketini oluştur, `/scan`'i dinleyip `/engel_durumu` yayınlayan node yaz | Yok, sahte `/scan` ile bağımsız test edilebilir |
| Üye-1, Üye-2 | Bu gece beklemede (ML/algılama işi sonraki aşamaya bırakıldı) | — |

## Topic Sözleşmesi (Kod yazmadan önce bunu değiştirmeyin)

| Topic | Tip | Yayınlayan | Dinleyen | Durum |
|---|---|---|---|---|
| `/odom` | `nav_msgs/msg/Odometry` | Gazebo diff-drive plugin | Üye-3, waypoint_controller | ✅ Çalışıyor |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | waypoint_controller | Gazebo diff-drive plugin, can_bridge_stub | ✅ Çalışıyor |
| `/scan` | `sensor_msgs/msg/LaserScan` | Gazebo lidar plugin | Üye-4 (obstacle_avoidance_node) | ✅ Çalışıyor |
| `/robotaksi/odom` | `nav_msgs/msg/Odometry` | Üye-3 (odom_relay_node) | (gelecekte: mission node) | 🔲 Yazılacak |
| `/engel_durumu` | `std_msgs/msg/Bool` | Üye-4 (obstacle_avoidance_node) | waypoint_controller | 🔲 Yazılacak |
| `/engel_mesafesi` | `std_msgs/msg/Float32` | Üye-4 (obstacle_avoidance_node) | waypoint_controller (opsiyonel) | 🔲 Yazılacak |
| `/beemobs/AUTONOMOUS_SteeringMot_Control` | `std_msgs/msg/Int32` (PWM 0-255) | Üye-5 (can_bridge_stub) | — (rapor kanıtı, gerçek CAN yok) | 🔲 Yazılacak |
| `/beemobs/RC_THRT_DATA` | `std_msgs/msg/Int32` (50-250) | Üye-5 (can_bridge_stub) | — | 🔲 Yazılacak |

**Üye-4 için not:** `/engel_durumu`'yu test ederken gerçek lidar koduna gerek
yok — terminalden manuel yayınlayıp waypoint_controller'in tepkisini test
edebilirsin:
```bash
ros2 topic pub /engel_durumu std_msgs/msg/Bool "data: true"
```

Bir topic adını veya tipini değiştirmeniz gerekiyorsa, push etmeden önce takıma
haber verin — aksi halde başkasının node'u sessizce çalışmaz hale gelir.

## Sorun Giderme

- **Gazebo GUI açılmıyor / boş pencere:** `xhost +local:docker` komutunu host
  terminalinde (container dışında) tekrar çalıştırın.
- **`colcon build` hata veriyor:** Önce `rm -rf build install log` ile temiz
  build deneyin (mount edilen klasördeki eski build artifact'leri sorun
  çıkarabilir).
- **Container zaten çalışıyor hatası:** `make stop`, sonra tekrar `make run`.