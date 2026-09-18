# Bemutató: C70 kamera és épülő 2D LiDAR-térkép

## Állapot és helyreállítás (2026-09-18)

A repó `60ec0d5` commitjáról induló helyi módosítás a meglévő `scripts/dashboard.html` oldalra tett `/map` (`nav_msgs/OccupancyGrid`) panelt, a C70 kamerakép mellé. A `control_panel.html` ezt az oldalt továbbra is beágyazza. A panel a foglaltsági rácsot rajzolja, megmutatja a felbontást és a frame nevét, és jelzi, ha 15 másodpercig nem érkezik friss térképüzenet. A nyers `/scan` felülnézete külön marad: nem nevezhető SLAM-térképnek.

A robot `192.168.123.50` címén a 22, 8901 és 9090-es port elérhető volt; a `control_panel.html` HTTP 200 választ adott. A 8080-as `web_video_server` port nem válaszolt. A rosbridge `/rosapi` lekérdezése szerint a `/scan`, `/usb_cam/image_raw` és `/map` témáknak **nem volt publikálója**; a látható node-ok: `/wheeltec_robot`, `/robot_pose_ekf`, `/robot_state_publisher`, `/joint_state_publisher`, `/rosbridge_websocket`, `/rosapi`, `/rosout`. A `/PowerVoltage` publikálója `/wheeltec_robot` volt, de a 16 másodperces feliratkozás nem kapott üzenetet. A `/tf_static` tartalmazta a `base_footprint → laser` kapcsolatot; ez önmagában nem bizonyítja, hogy az aktuális `/scan` időbélyege a dinamikus odometriával összeilleszthető. Az első hálózati méréskor a systemd unitok még nem voltak olvashatók; az alábbi SSH-mérés ezt pótolta. A repóban lévő HTML-módosítások **nincsenek a robotra telepítve**.

Korábbi, külön sessionben dokumentált mérés szerint a C70 adott képet és a LiDAR kb. 12 Hz-cel mért, de a gmapping 100% mérést dobott el, `/map` nélkül. Ez nem írja felül a fenti aktuális, szenzor-publikálók nélküli állapotot.

**A helyreállítás előtti SSH-ellenőrzés:** a három `pickerbot-*` systemd-szolgáltatás futott. A gyári `turn_on_wheeltec_robot.launch` már 13:30-tól egy külön, korábbi SSH-sessionből maradt árva `roslaunch` folyamatban futott, majd 13:32-kor a systemd másodszor is elindította. A második indítás naplójában `serial::SerialException` és több azonos nevű ROS-node ütközése látszott. A ROS master még hirdette a `/wheeltec_robot` node-ot, de a `rosnode ping` sikertelen volt, és a driverfolyamat hiányzott. A `/PowerVoltage` és `/odom` ekkor nem adott friss értéket.

A systemd eredeti `ExecStart` sora paraméter nélkül indította a gyári launch-t; a korábbi `/wheeltec_robot/car_mode` érték `senior_mec_bs` volt, holott a Xavier dokumentált módja `mini_mec_moveit_four`. A `/dev/wheeltec_controller` létezik és `/dev/ttyCH343USB1`-re mutat. Az aktív USB-LAN adapter az `eth0`, rajta `192.168.123.50/24` címmel; a sérült beépített `eth1` `NO-CARRIER`. Aktuális `/scan` üzenet még nincs, így a scan és TF időbélyegeit még nem lehet összevetni.

**Jóváhagyott karbantartás 14:28–14:30 CEST:** a meglévő gyári launch-fájlt változatlanul hagytuk. A `/etc/systemd/system/pickerbot-bringup.service.d/10-xavier-model.conf` drop-in az `ExecStart` sorhoz `car_mode:=mini_mec_moveit_four` értéket ad. A rosbridge-et és a systemd bringupot leállítottuk, majd az árva `roslaunch` folyamatot `SIGINT` jellel szabályosan lezártuk. A ROS master portja ezután felszabadult. Az egyetlen bringupot újraindítottuk, majd a rosbridge-et is. A három systemd-szolgáltatás újra aktív és engedélyezett; a webes vezérlőpult HTTP 200 választ ad. A `/wheeltec_robot` node pingelhető, a `car_mode` `mini_mec_moveit_four`, a `/odom` és `/imu` friss, a `/PowerVoltage` 23,29–23,31 V volt. Egy 10 másodperces rosbridge mérés 19 odometria-, 19 IMU- és 15 feszültségüzenetet kapott. Nem küldtünk mozgás- vagy karparancsot.

**Első rebootpróba és javítása:** a bringup és a rosbridge `active` állapota eleinte félrevezető volt: mindkét `roslaunch` a 11311-es porton saját ROS mastert próbált indítani, mert a rosbridge `After=pickerbot-bringup.service` függése csak a service indulását, nem a master készültségét várta meg. Portütközés és automatikus újraindítási kör lett az eredmény. A `/etc/systemd/system/pickerbot-rosbridge.service.d/10-wait-for-master.conf` drop-in most a `/run_id` ROS-paraméter sikeres lekérdezéséig vár (legfeljebb 60 másodpercig), és a helyi ROS master címét használja. A két drop-in pontos tartalma a repó [systemd/](../systemd/) mappájában van.

**Második rebootpróba sikeres (14:39 CEST):** a bringup és a rosbridge `NRestarts=0` értékkel, a helyes sorrendben indult; pontosan egy `roslaunch` és egy ROS master futott. A `/wheeltec_robot` válaszolt, a `car_mode` `mini_mec_moveit_four`, a `/PowerVoltage` 23,33 V, az `/odom` friss `odom_combined` frame-ben. A rosbridge 10 másodperc alatt 19 odometria-, 19 IMU- és 16 feszültségüzenetet továbbított; a vezérlőpult HTTP 200 választ adott. A friss `/scan`, `/usb_cam/image_raw` és `/map` továbbra is hiányzik. Fizikai kontrollerrel mozgáspróba nem történt.

**Következő, csak olvasó szenzorleltár ugyanazon a napon:** a C70 eszköznév `/dev/RgbCam → video0`; `/dev/video0` és `/dev/video1` látszik. Az Astra `/dev/astra_s → bus/usb/001/004` néven jelenik meg. `/dev/ttyCH343USB0` és `/dev/ttyCH343USB1` is létezik, de a LiDAR tényleges soros portját ebből még nem igazoltuk. A gyári `wheeltec_lidar.launch` alapértelmezett módja `ls_M10P_uart`, míg a régi `start_feeds.sh` külön indította a LiDAR-, C70-, Astra- és `web_video_server` folyamatokat. A `/dev/lslidar` név nem létezik. Ezen a ponton nem indítottunk szenzornode-ot, mert a cél a dokumentálás és a stabil robotállapot megőrzése volt.

**Pontosan mi változott a roboton:** egy új SSH publikus kulcs került a `wheeltec` felhasználó kulcslistájába; két systemd drop-in készült a fent megadott útvonalakon. A gyári launch-fájlok, a robot firmware-e és a webes HTML-fájlok nem változtak. A régi árva `roslaunch` folyamatot egyszer `SIGINT` jellel lezártuk; a három meglévő service közül a bringupot és a rosbridge-et a javítás során leállítottuk és újraindítottuk, majd két kontrollált reboot történt. Az első reboot az indulási versenyt feltárta, a második a javítást igazolta. A systemd-fájlok a repó `systemd/` mappájában pontos másolatként szerepelnek; SHA-256 ellenőrzésük a roboton lévő példányokkal egyezett.

**Visszaállítás, ha szükséges:** a két drop-in külön eltávolítható, utána `sudo systemctl daemon-reload` és a hozzá tartozó service újraindítása kell. A `10-xavier-model.conf` eltávolítása visszahozza a gyári `senior_mec_bs` alapértelmezést, ezért ezt csak tudatosan tedd. A `10-wait-for-master.conf` eltávolítása reboot után ismét a ROS master indulási versenyét okozhatja. A nyilvános SSH-kulcs azonosítója `pickerbot-mini-codex`; szükség esetén csak ezt az egy sort távolítsd el az `authorized_keys` fájlból.

## Következő, csak olvasó robotoldali ellenőrzés

A kulcsos SSH-hozzáférés ezen a gépen már működik, a segédprogram a helyi Documents/Codex/pickerbot-access/connect.ps1 fájl. A parancsok nem indítanak új drivert és nem mozgatják a robotot.

```bash
source /opt/ros/noetic/setup.bash
source /home/wheeltec/wheeltec_robot/devel/setup.bash
ip -br addr
ip -br link
systemctl status pickerbot-bringup pickerbot-rosbridge pickerbot-webui --no-pager
systemctl cat pickerbot-bringup pickerbot-rosbridge pickerbot-webui
ss -ltnp | grep -E ':(8080|8901|9090|11311)\b'
rostopic info /PowerVoltage
timeout 8 rostopic echo -n 1 /PowerVoltage
rostopic info /usb_cam/image_raw
rostopic info /scan
rostopic info /map
rosnode list
```

Az USB-LAN adapteren ellenőrizd a `192.168.123.50/24` címet és a fizikai linket. A dokumentált három szolgáltatás nem bizonyítja, hogy a C70, a LiDAR, a videószerver és a SLAM is indul. Az ezekhez tartozó meglévő indítási láncot előbb fel kell térképezni; a régi `scripts/start_feeds.sh` szkriptet ne indítsd párhuzamosan vakon.

**Megismétlődés megelőzése:** a rendszerindításkor a systemd már elindítja az egyetlen, helyes modellű bringupot. Kézzel ne futtasd mellé a `turn_on_wheeltec_robot.launch` fájlt vagy a régi `start_feeds.sh` szkriptet; előbb a futó node-okat és folyamatokat ellenőrizd. A drop-in eltávolításával és `systemctl daemon-reload` hívással az eredeti service konfiguráció visszaállítható, de ez ismét a rossz alapértelmezett modellt használná.

## A gmapping diagnózisa

Csak akkor kezdd, ha a `/scan`-nek már van publikálója és friss üzenete. A gyári `mapping.launch` egészét ne indítsd a futó bringup mellé, mert az alvázvezérlést is újraindíthatja.

```bash
rostopic hz /scan
timeout 8 rostopic echo -n 1 /scan/header
timeout 8 rostopic echo -n 1 /odom/header
rostopic hz /tf
rosrun tf tf_echo odom_combined laser
```

Jegyezd fel ugyanabban a mérési ablakban a `/scan/header.frame_id` és `stamp`, az `/odom` és `/tf` időbélyegeit, a ROS-időt (`rosparam get /use_sim_time`, `rostopic echo -n 1 /clock` csak ha szimulált idő aktív), valamint a TF-útvonalat a scan frame-jétől az `odom_combined` frame-ig. A korábbi `MessageFilter [target=odom_combined]: Dropped 100.00%` hiba okát csak ebből lehet azonosítani: lehet hiányzó transzformáció, rossz frame név, túl régi/jövőbeli stamp vagy késő TF. A `base_footprint → laser` statikus kapcsolat önmagában kevés.

A SLAM indítását a meglévő bringup pontos tartalma alapján külön, Dockerben tervezd meg úgy, hogy ne indítson második `/wheeltec_robot` vagy szenzor-drivert. A cél igazolása: a `/map`-nek tényleges publikálója van, legalább két friss `OccupancyGrid` üzenet érkezik mozgás közben, és a rács tartalma változik. Az egyetlen latchelt térképüzenet még nem bizonyítja az épülő térképet.

## Hálózat és főpróba

A jelenlegi rosbridge elérhető a közös robot-hálóról a 9090-es porton. A systemd a gyári rosbridge_websocket.launch fájlt indítja külön témaszűkítés nélkül, a socket pedig 0.0.0.0:9090 címen figyel. A bemutatóhoz csak a kijelzőt adó laptopról legyen elérhető a vezérlési kapcsolat; a rosbridge téma- és szolgáltatáslistáját a tényleges használathoz kell szűkíteni. A robot gyári rendszerének módosítása helyett új robotoldali szoftver csak Dockerben fusson. A már létező, hoszton futó három systemd szolgáltatás és ez a szabály közti eltérést a tulajdonossal tisztázni kell, mielőtt a host szolgáltatásait átállítjuk.

Kijelzőnek elsőként a laptophoz kötött külső monitort használd, és a `control_panel.html` oldalt nyisd meg teljes képernyőn. A képen a C70 és a `/map` panel egymás mellett van. Ha a térkép csak „várakozás” vagy „nem frissül” állapotot mutat, a bemutató térképes része még nincs kész; ne helyettesítsd a nyers `/scan` panellel. A laptop és a külső monitor kapcsolatát, felbontását és a robotra telepített új HTML-t a helyszínen kell igazolni.

Mozgáspróbát csak feltöltött akkumulátorral, a `/PowerVoltage` friss értékének ellenőrzése után, rendezett kábelekkel, a kerekektől távol lévő tárgyakkal, és kéznél levő **fizikai** leállítással végezz. A korábbi webes E-STOP nem állította meg időben a mozgást; ennek oka nincs bizonyítva. A fizikai kontroller működéséről korábbi felhasználói beszámoló van, a friss reboot utáni főpróba még hiányzik. A kar webes panelje továbbra is szimuláció, a `/camera/toggle_ir` hívást nem szabad használni.
