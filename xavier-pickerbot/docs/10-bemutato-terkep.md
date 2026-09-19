# Bemutató: C70 kamera és épülő 2D LiDAR-térkép

## Állapot és helyreállítás (2026-09-18)

A repó `60ec0d5` commitjáról induló helyi módosítás a meglévő `scripts/dashboard.html` oldalra tett `/map` (`nav_msgs/OccupancyGrid`) panelt, a C70 kamerakép mellé. A `control_panel.html` ezt az oldalt továbbra is beágyazza. A panel a foglaltsági rácsot rajzolja, megmutatja a felbontást és a frame nevét, és jelzi, ha 15 másodpercig nem érkezik friss térképüzenet. A nyers `/scan` felülnézete külön marad: nem nevezhető SLAM-térképnek.

A robot `192.168.123.50` címén a 22, 8901 és 9090-es port elérhető volt; a `control_panel.html` HTTP 200 választ adott. A 8080-as `web_video_server` port nem válaszolt. A rosbridge `/rosapi` lekérdezése szerint a `/scan`, `/usb_cam/image_raw` és `/map` témáknak **nem volt publikálója**; a látható node-ok: `/wheeltec_robot`, `/robot_pose_ekf`, `/robot_state_publisher`, `/joint_state_publisher`, `/rosbridge_websocket`, `/rosapi`, `/rosout`. A `/PowerVoltage` publikálója `/wheeltec_robot` volt, de a 16 másodperces feliratkozás nem kapott üzenetet. A `/tf_static` tartalmazta a `base_footprint → laser` kapcsolatot; ez önmagában nem bizonyítja, hogy az aktuális `/scan` időbélyege a dinamikus odometriával összeilleszthető. Az első hálózati méréskor a systemd unitok még nem voltak olvashatók; az alábbi SSH-mérés ezt pótolta. A repóban lévő HTML-módosítások **nincsenek a robotra telepítve**.

Korábbi, külön sessionben dokumentált mérés szerint a C70 adott képet és a LiDAR kb. 12 Hz-cel mért, de a gmapping 100% mérést dobott el, `/map` nélkül. Ez nem írja felül a fenti aktuális, szenzor-publikálók nélküli állapotot.

**A helyreállítás előtti SSH-ellenőrzés:** a három `pickerbot-*` systemd-szolgáltatás futott. A gyári `turn_on_wheeltec_robot.launch` már 13:30-tól egy külön, korábbi SSH-sessionből maradt árva `roslaunch` folyamatban futott, majd 13:32-kor a systemd másodszor is elindította. A második indítás naplójában `serial::SerialException` és több azonos nevű ROS-node ütközése látszott. A ROS master még hirdette a `/wheeltec_robot` node-ot, de a `rosnode ping` sikertelen volt, és a driverfolyamat hiányzott. A `/PowerVoltage` és `/odom` ekkor nem adott friss értéket.

A systemd eredeti `ExecStart` sora paraméter nélkül indította a gyári launch-t; a korábbi `/wheeltec_robot/car_mode` érték `senior_mec_bs` volt, holott a Xavier dokumentált módja `mini_mec_moveit_four`. A `/dev/wheeltec_controller` létezik és `/dev/ttyCH343USB1`-re mutat. Az aktív USB-LAN adapter az `eth0`, rajta `192.168.123.50/24` címmel; a sérült beépített `eth1` `NO-CARRIER`. Aktuális `/scan` üzenet még nincs, így a scan és TF időbélyegeit még nem lehet összevetni.

**Jóváhagyott karbantartás 14:28–14:30 CEST:** a meglévő gyári launch-fájlt változatlanul hagytuk. A `/etc/systemd/system/pickerbot-bringup.service.d/10-xavier-model.conf` drop-in az `ExecStart` sorhoz `car_mode:=mini_mec_moveit_four` értéket ad. A rosbridge-et és a systemd bringupot leállítottuk, majd az árva `roslaunch` folyamatot `SIGINT` jellel szabályosan lezártuk. A ROS master portja ezután felszabadult. Az egyetlen bringupot újraindítottuk, majd a rosbridge-et is. A három systemd-szolgáltatás újra aktív és engedélyezett; a webes vezérlőpult HTTP 200 választ ad. A `/wheeltec_robot` node pingelhető, a `car_mode` `mini_mec_moveit_four`, a `/odom` és `/imu` friss, a `/PowerVoltage` 23,29–23,31 V volt. Egy 10 másodperces rosbridge mérés 19 odometria-, 19 IMU- és 15 feszültségüzenetet kapott. Nem küldtünk mozgás- vagy karparancsot.

**Első rebootpróba és javítása:** a bringup és a rosbridge `active` állapota eleinte félrevezető volt: mindkét `roslaunch` a 11311-es porton saját ROS mastert próbált indítani, mert a rosbridge `After=pickerbot-bringup.service` függése csak a service indulását, nem a master készültségét várta meg. Portütközés és automatikus újraindítási kör lett az eredmény. A `/etc/systemd/system/pickerbot-rosbridge.service.d/10-wait-for-master.conf` drop-in most a `/run_id` ROS-paraméter sikeres lekérdezéséig vár (legfeljebb 60 másodpercig), és a helyi ROS master címét használja. A két drop-in pontos tartalma a repó [systemd/](../systemd/) mappájában van.

**Második rebootpróba sikeres (14:39 CEST):** a bringup és a rosbridge `NRestarts=0` értékkel, a helyes sorrendben indult; pontosan egy alváz-bringup és egy ROS master futott. A `/wheeltec_robot` válaszolt, a `car_mode` `mini_mec_moveit_four`, a `/PowerVoltage` 23,33 V, az `/odom` friss `odom_combined` frame-ben. A rosbridge 10 másodperc alatt 19 odometria-, 19 IMU- és 16 feszültségüzenetet továbbított; a vezérlőpult HTTP 200 választ adott. A friss `/scan`, `/usb_cam/image_raw` és `/map` továbbra is hiányzik. Fizikai kontrollerrel mozgáspróba nem történt.

**Következő, csak olvasó szenzorleltár ugyanazon a napon:** a C70 eszköznév `/dev/RgbCam → video0`; `/dev/video0` és `/dev/video1` látszik. Az Astra `/dev/astra_s → bus/usb/001/004` néven jelenik meg. `/dev/ttyCH343USB0` és `/dev/ttyCH343USB1` is létezik, de a LiDAR tényleges soros portját ebből még nem igazoltuk. A gyári `wheeltec_lidar.launch` alapértelmezett módja `ls_M10P_uart`, míg a régi `start_feeds.sh` külön indította a LiDAR-, C70-, Astra- és `web_video_server` folyamatokat. A `/dev/lslidar` név nem létezik. Ezen a ponton nem indítottunk szenzornode-ot, mert a cél a dokumentálás és a stabil robotállapot megőrzése volt.

**Pontosan mi változott a roboton:** egy új SSH publikus kulcs került a `wheeltec` felhasználó kulcslistájába; két systemd drop-in készült a fent megadott útvonalakon. A gyári launch-fájlok, a robot firmware-e és a webes HTML-fájlok nem változtak. A régi árva `roslaunch` folyamatot egyszer `SIGINT` jellel lezártuk; a három meglévő service közül a bringupot és a rosbridge-et a javítás során leállítottuk és újraindítottuk, majd két kontrollált reboot történt. Az első reboot az indulási versenyt feltárta, a második a javítást igazolta. A systemd-fájlok a repó `systemd/` mappájában pontos másolatként szerepelnek; SHA-256 ellenőrzésük a roboton lévő példányokkal egyezett.

**Visszaállítás, ha szükséges:** a két drop-in külön eltávolítható, utána `sudo systemctl daemon-reload` és a hozzá tartozó service újraindítása kell. A `10-xavier-model.conf` eltávolítása visszahozza a gyári `senior_mec_bs` alapértelmezést, ezért ezt csak tudatosan tedd. A `10-wait-for-master.conf` eltávolítása reboot után ismét a ROS master indulási versenyét okozhatja. A nyilvános SSH-kulcs azonosítója `pickerbot-mini-codex`; szükség esetén csak ezt az egy sort távolítsd el az `authorized_keys` fájlból.

## Repozitóriumban rögzített munka

A módosítások a `codex/pickerbot-demo-20260918` Git-ágban vannak. A `main` ág munkakönyvtára tiszta maradt. A `scripts/dashboard.html` megjeleníti a valódi `/map` foglaltsági rácsot és az üzenet frissességét; a `scripts/control_panel.html` beágyazási mérete és a vezérlés szövege frissült. A `scripts/xavier_control/base_drive.py` régi megjegyzése pontosítva lett. A README, a hozzáférési, kezelőpult-, kézi vezérlési és hálózati dokumentáció, valamint ez a napló frissült. A két telepített systemd drop-in pontos másolata a `systemd/` mappában szerepel; ezek bájtonkénti SHA-256 ellenőrzése egyezett a roboton lévő fájlokkal.

A JavaScript szintaxisellenőrzés és a szintetikus `OccupancyGrid`-megjelenítési próba sikeres volt; a Git diff whitespace-ellenőrzése sem talált hibát. Az új HTML nincs a robotra telepítve, és élő térképpel még nem tesztelhető, mert a `/map` témának nincs publikálója. A roboton ezen a napon csak a fent felsorolt SSH-kulcs és két systemd drop-in változott. A dokumentáció lezárása után további robotoldali módosítás nem történt.

## 2026-09-19: C70 kamera helyreállítása

A robot újra elérhető volt. A három `pickerbot-*` systemd-szolgáltatás aktív, a bringup és a rosbridge `NRestarts=0` értékű. A `/PowerVoltage` publikálója továbbra is az alváz node-ja; a `/scan`, `/usb_cam/image_raw` és `/map` a munka kezdetén hiányzott. A gyári `wheeltec_lidar.launch` az `ls_M10P_uart` módot és a `lslidar_serial.launch` fájlt választja; utóbbi `/dev/wheeltec_lidar` eszközt vár. A LiDAR udev-szabály a `0001` sorozatszámú `/dev/ttyCH343USB0` porthoz rendeli ezt a nevet, az alváz `0002` sorozatszámú portja a `/dev/ttyCH343USB1`. Az udev-szabály csak olvasó ellenőrzése után a LiDAR-link láthatóvá vált. A gyári launch-fájlok és udev-szabályok nem változtak.

A felhasználó a kameraképet helyezte előtérbe. A roboton lévő egyetlen korábbi Docker-kép ROS Melodicot tartalmazott; letöltöttük a `ros:noetic-ros-base-focal` ARM64 alapképet (`sha256:72b8bc59035dc0a5b8e07aae28c16caa84192971d72d207c72ed734fb1d5e97d`). Az első, LiDAR-t és kamerát együtt építő kísérlet túl nagy PCL-függőségi láncot kezdett telepíteni, ezért a célzott build-konténert leállítottuk; szenzort nem indított. Az ideiglenes LiDAR buildmappát töröltük. Helyette a [docker/sensors/](../docker/sensors/) mappában reprodukálható, kisebb C70-képet készítettünk. Az élő roboton ennek buildkontextusa `/home/wheeltec/pickerbot-c70-build-20260919/`, a kész image `pickerbot/c70:noetic-20260919`.

A `/dev/RgbCam → /dev/video0` kamera szabad volt, és a 640×480 YUYV módot 30 kép/s hardverképességgel hirdette. Előbb eltávolítható próbakonténerben, majd `--restart unless-stopped` szabállyal a `pickerbot-c70` Docker-konténerben indult a `usb_cam_node`. A `/usb_cam/image_raw` `sensor_msgs/Image` témán friss, `c70_cam` frame nevű kép érkezett; a nyolc másodperces mérés kb. 15 kép/s sebességet adott. A `pickerbot-web-video` konténer ugyanebből az image-ből fut. A 8080-as porton MJPEG-folyamot ad; három másodperc alatt HTTP 200 mellett 3,9 MB adat érkezett a próba során. A tartós változat **csak `127.0.0.1:8080` címen figyel**: helyben két másodperc alatt HTTP 200 és 2,46 MB adat, míg a robot LAN-címén a kapcsolat elutasított. Mindkét konténer `running` állapotú és `unless-stopped` újraindítási szabályú. A konténerek reboot utáni viselkedését még nem próbáltuk ki.

A laptopon a [scripts/start-demo-view.ps1](../scripts/start-demo-view.ps1) helyi HTTP-szervert és SSH-alagutat indít, majd a friss `dashboard.html` oldalt nyitja meg. A [scripts/stop-demo-view.ps1](../scripts/stop-demo-view.ps1) ezeket a helyi folyamatokat állítja le. A laptopon a dashboard és az alagúton át elért videószerver is HTTP 200 választ adott. A roboton korábban telepített 8901-es weboldal továbbra is a régi HTML-t szolgálja ki; nem írtuk át. A kamera tényleges képtartalmának helyi exportját az automatikus jóváhagyási ellenőrzés érzékeny felvétel lehetősége miatt elutasította, ezért a kép vizuális minősége nincs igazolva. A webes folyam és a ROS-képkockák működését igazoltuk. A mérési MJPEG ideiglenes fájlját töröltük.

### 2026-09-19: Üres kameramező a laptop böngészőjében

A helyi `8902`-es dashboard tovább működött, de a `127.0.0.1:8080` SSH-alagút időnként megszakadt, ezért a C70 mező üres lett. Egy újraindítás után a helyi MJPEG-végpont HTTP 200 választ adott, 3 másodperc alatt 2,9 MB képadattal, később az alagút ismét kiesett. A roboton a `/usb_cam/image_raw` továbbra is `rgb8`, 640×480, `step=1920` formátumú; a rosbridge és a `/map` működött. A hiba a laptop videókapcsolatánál volt, nem a kamera ROS-publikálásánál.

A [scripts/dashboard.html](../scripts/dashboard.html) a C70 és térkép párost most az oldal tetejére teszi, az inaktív Astra mező elé. A kameraállapot kiírja, hogy MJPEG vagy tartalék ROS-kép érkezik-e. MJPEG-hiba esetén a böngésző a meglévő `9090`-es rosbridge kapcsolaton feliratkozik a `/usb_cam/image_raw` témára, ritkított üzeneteket RGB canvason rajzol, és jelzi, ha a kép nem frissül. Az in-app böngészőben mind az „élő MJPEG”, mind a „ROS-kép · 640×480” állapot megjelent; a térkép közben 384×384 cellás friss üzeneteket mutatott. A vizuális képminőséget továbbra is a felhasználónak kell megítélnie. A tömörített ROS-képhez a robot kamerakonténerét újra kellene építeni; ez a jelenlegi működéshez nem szükséges, ezért a roboton nem változtattunk.

Az alváz bringup, a rosbridge, a webui, a gyári launch-fájlok és a firmware nem változtak. A roboton ebben a szakaszban két új Docker-konténer és egy buildkontextus maradt; az új laptopos nézet elindult. A `/scan` és a `/map` ekkor még hiányzott. Leállítás és újbóli indítás: [docker/sensors/README.md](../docker/sensors/README.md).

## 2026-09-19: LiDAR és élő SLAM-térkép

A gyári LiDAR-node fordított állománya és három saját megosztott könyvtára a roboton megvolt. Az első teljes újrafordítás túl nagy PCL-függőségi lánca helyett ezeket a meglévő állományokat külön ARM64 Noetic Docker-képbe csomagoltuk; a gyári forrást nem módosítottuk. A buildkontextus `/home/wheeltec/pickerbot-lidar-build-20260919/`, az image `pickerbot/lidar:noetic-20260919`. A pontos állományok, SHA-256 értékek, paraméterek és visszaállítás: [docker/lidar/README.md](../docker/lidar/README.md). A képen belüli `ldd` minden futásidejű függőséget megtalált. A `/dev/wheeltec_lidar` eszközt egyedül ez a konténer kapta meg; az alváz külön soros portjához nem nyúltunk.

Az eltávolítható próbakonténerben a `/lslidar_driver_node` válaszolt és a `/scan` `laser` frame-ben kb. **12 Hz** sebességgel publikált. A `tf_echo odom_combined laser` élő transzformációt adott; a scan és az odometria időbélyegei az aktuális ROS-időben voltak. Ezután a próbakonténert leállítottuk, és ugyanebből az image-ből a `pickerbot-lidar` konténert `unless-stopped` szabállyal indítottuk. Második LiDAR-node nem fut.

A gmapping külön, `pickerbot/slam:noetic-20260919` image-ben fut. Csak a `slam_gmapping` node-ot indítja, nem a gyári `mapping.launch` teljes láncát. A konfiguráció és visszaállítás: [docker/slam/README.md](../docker/slam/README.md). A próbakonténerben a gmapping naplója feldolgozott scane-ket és sikeres scanillesztést mutatott, majd a `/map` `nav_msgs/OccupancyGrid` publikálója megjelent. Egy 384×384 cellás, 0,05 m felbontású rácsban 4559 szabad és 412 foglalt cellát mértünk; nyolc másodperc alatt öt külön időbélyegű és különböző tartalmú térképüzenet érkezett. A próbakonténert leállítottuk, és a `pickerbot-slam` konténert `unless-stopped` szabállyal indítottuk. A tartós változatban a `/map` újra elérhető volt. Az alváz node-ja eközben tovább válaszolt, és a három korábbi systemd-szolgáltatás aktív maradt.

A robot állt a mérés közben. Az eltérő térképrácsok önmagukban nem bizonyítják, hogy haladás közben a környezet helyesen épül fel; ezt fizikai kontrollerrel, kéznél lévő leállítással kell kipróbálni. Az új Docker-konténerek reboot utáni indulása és a helyi irányítópult tényleges képi megjelenése is ellenőrzendő. A roboton most négy új Docker-konténer fut: `pickerbot-c70`, `pickerbot-web-video`, `pickerbot-lidar`, `pickerbot-slam`.

## Állapotellenőrzés a következő alkalommal

Az eredeti `scripts/start_feeds.sh` önálló `roscore`-t és `rosbridge_websocket`-et is indítana; ezeket most a systemd-szolgáltatások adják. Az Astra kamera továbbra sem fut. A teljes régi szkriptet a jelenlegi rendszer mellé ne indítsd, mert duplázhatja a node-okat és a portokat.

A kulcsos SSH-hozzáférés ezen a gépen már működik, a segédprogram a helyi Documents/Codex/pickerbot-access/connect.ps1 fájl. A parancsok nem indítanak új drivert és nem mozgatják a robotot.

```bash
source /opt/ros/noetic/setup.bash
source /home/wheeltec/wheeltec_robot/devel/setup.bash
ip -br addr
ip -br link
systemctl status pickerbot-bringup pickerbot-rosbridge pickerbot-webui --no-pager
systemctl cat pickerbot-bringup pickerbot-rosbridge pickerbot-webui
sudo docker ps --format '{{.Names}} {{.Status}}'
ss -ltnp | grep -E ':(8080|8901|9090|11311)\b'
rostopic info /PowerVoltage
timeout 8 rostopic echo -n 1 /PowerVoltage
rostopic info /usb_cam/image_raw
rostopic info /scan
rostopic info /map
rosnode list
```

Az USB-LAN adapteren ellenőrizd a `192.168.123.50/24` címet és a fizikai linket. A három systemd-szolgáltatás és a négy Docker-konténer állapotát külön ellenőrizd; a `running` állapot mellett a fenti ROS-témák friss üzenetei is szükségesek. A 8080-as portnak csak a robot `127.0.0.1` címén szabad figyelnie.

**Megismétlődés megelőzése:** a rendszerindításkor a systemd már elindítja az egyetlen, helyes modellű bringupot. Kézzel ne futtasd mellé a `turn_on_wheeltec_robot.launch` fájlt vagy a régi `start_feeds.sh` szkriptet; előbb a futó node-okat és folyamatokat ellenőrizd. A drop-in eltávolításával és `systemctl daemon-reload` hívással az eredeti service konfiguráció visszaállítható, de ez ismét a rossz alapértelmezett modellt használná.

## A gmapping további ellenőrzése

A `/scan` és a `/map` jelenleg publikál. A gyári `mapping.launch` egészét ne indítsd a futó bringup mellé, mert az alvázvezérlést is újraindíthatja. Ha reboot után eltűnik a térkép, előbb a Docker-konténerek állapotát, a LiDAR-linket, a scan és odometria időbélyegeit, majd a TF-útvonalat ellenőrizd.

```bash
rostopic hz /scan
timeout 8 rostopic echo -n 1 /scan/header
timeout 8 rostopic echo -n 1 /odom/header
rostopic hz /tf
rosrun tf tf_echo odom_combined laser
```

Jegyezd fel ugyanabban a mérési ablakban a `/scan/header.frame_id` és `stamp`, az `/odom` és `/tf` időbélyegeit, a ROS-időt (`rosparam get /use_sim_time`, `rostopic echo -n 1 /clock` csak ha szimulált idő aktív), valamint a TF-útvonalat a scan frame-jétől az `odom_combined` frame-ig. A korábbi `MessageFilter [target=odom_combined]: Dropped 100.00%` hiba okát csak ebből lehet azonosítani: lehet hiányzó transzformáció, rossz frame név, túl régi/jövőbeli stamp vagy késő TF. A `base_footprint → laser` statikus kapcsolat önmagában kevés.

A külön Dockeres SLAM most fut, második `/wheeltec_robot` nélkül. A következő cél annak igazolása, hogy fizikai kontrolleres mozgás közben legalább két friss `OccupancyGrid` üzenet érkezik és a helyesen tájolt rács tartalma változik. Az álló helyzetben megfigyelt eltérő rácsok ezt még nem bizonyítják.

## Hálózat és főpróba

A jelenlegi rosbridge elérhető a közös robot-hálóról a 9090-es porton. A systemd a gyári rosbridge_websocket.launch fájlt indítja külön témaszűkítés nélkül, a socket pedig 0.0.0.0:9090 címen figyel. A bemutatóhoz csak a kijelzőt adó laptopról legyen elérhető a vezérlési kapcsolat; a rosbridge téma- és szolgáltatáslistáját a tényleges használathoz kell szűkíteni. A robot gyári rendszerének módosítása helyett új robotoldali szoftver csak Dockerben fusson. A már létező, hoszton futó három systemd szolgáltatás és ez a szabály közti eltérést a tulajdonossal tisztázni kell, mielőtt a host szolgáltatásait átállítjuk.

Kijelzőnek elsőként a laptophoz kötött külső monitort használd, és a `scripts/start-demo-view.ps1` indítóval megnyitott helyi `dashboard.html` oldalt tedd teljes képernyőre. A C70 és a `/map` panel egymás mellett van. Ha a térkép csak „várakozás” vagy „nem frissül” állapotot mutat, a bemutató térképes része nem kész; ne helyettesítsd a nyers `/scan` panellel. A laptop és a külső monitor kapcsolatát, felbontását és a tényleges képminőséget a helyszínen kell igazolni.

Mozgáspróbát csak feltöltött akkumulátorral, a `/PowerVoltage` friss értékének ellenőrzése után, rendezett kábelekkel, a kerekektől távol lévő tárgyakkal, és kéznél levő **fizikai** leállítással végezz. A korábbi webes E-STOP nem állította meg időben a mozgást; ennek oka nincs bizonyítva. A fizikai kontroller működéséről korábbi felhasználói beszámoló van, a friss reboot utáni főpróba még hiányzik. A kar webes panelje továbbra is szimuláció, a `/camera/toggle_ir` hívást nem szabad használni.
