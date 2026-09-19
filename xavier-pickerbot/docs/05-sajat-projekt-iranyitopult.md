# Saját projekt #1 — élő webes irányítópult

**2026-08-25-én szenzorokkal tesztelve.** A [scripts/control_panel.html](../scripts/control_panel.html) beágyazza a [scripts/dashboard.html](../scripts/dashboard.html) oldalt. A 2026-09-18-i mérésen a weboldal elérhető volt, de a kamera, LiDAR és SLAM publikálói hiányoztak. 2026-09-19-én a C70 képe Dockerből újra megjelent; a `/scan` és `/map` még hiányzik. Az aktuális laptopos nézet a [scripts/start-demo-view.ps1](../scripts/start-demo-view.ps1) indítóval érhető el; lásd [10-bemutato-terkep.md](10-bemutato-terkep.md).

## Mit tud

- **Két kamera élőben**, egy oldalon:
  - **Astra RGBD** → `/camera/rgb`, `/camera/depth`, (IR csak akkor, ha az RGB ki van kapcsolva — driver-korlát, egyszerre csak az egyik megy)
  - **Wheeltec C70** (a karra szerelt USB webkamera) → `/usb_cam/image_raw`
- **Kamera mód kapcsolók** (RGB/Depth be-ki) élő `std_srvs/SetBool` hívásokkal, relaunch nélkül a lapról.
- **Depth kép saját canvas-renderelése** — a `web_video_server` nem tudja a 16UC1 nyers mélységformátumot automatikusan színes képpé konvertálni (`cv_bridge` hiba: `[16UC1] is not a color format`), ezért ezt a lap saját JavaScript-je csinálja.
- **3D point cloud + LiDAR overlay**, Three.js + OrbitControls (kattints+húzd forgatáshoz, görgő zoomhoz) — `/camera/depth/points`-ból (kék), a LiDAR `/scan` ugyanabba a 3D térbe vetítve (narancssárga).
- **Valódi 2D SLAM-térkép panel** a C70 kép mellett: `/map` (`nav_msgs/OccupancyGrid`) foglaltsági rács, frissülési állapottal. Csak akkor mutat térképet, ha ROS-oldalon tényleges `/map` üzenet érkezik; roboton még nem teszteltük.

## Korábbi kézi indítás (2026-08-25)

Az alábbi eljárás a régi, külön szenzorindítás dokumentációja. A 2026-09-18 óta dokumentált automatikus systemd-szolgáltatások mellett a `start_feeds.sh`-t ne futtasd ellenőrzés nélkül, mert folyamatokat duplázhat. Az aktuális bemutató ellenőrzési sorrendje a [10-bemutato-terkep.md](10-bemutato-terkep.md) fájlban van.

```bash
# a roboton, SSH-n át:
ssh -i ~/.ssh/pickerbot_mini wheeltec@192.168.123.50 'bash -s' < scripts/start_feeds.sh
```

Elindítja: `roscore`, Astra kamera, LiDAR, C70 usb_cam, `web_video_server`, `rosbridge_websocket`.

```bash
# helyben, a scripts/ mappában:
python -m http.server 8901
```

Majd nyisd meg: `http://127.0.0.1:8901/dashboard.html` — **fontos: ne `file://`-ként**, mert az statikus pillanatképként fut, a WebSocket-kapcsolat el sem indul.

**Mai hozzáférés:** a videókiszolgáló csak a robot `127.0.0.1:8080` címén figyel. A laptopos indító SSH-alagutat nyit, így a helyi `http://127.0.0.1:8080/` kamera-lista elérhető. A korábbi `http://192.168.123.50:8080/` cím szándékosan nem működik. A Depth 16UC1 adatát továbbra is a dashboard saját canvas-renderje kezeli.

## Technikai buktatók, amiket ez a projekt oldott meg

1. **A rosbridge Base64-ként küldi a bájttömb mezőket.** A `PointCloud2.data` és `Image.data` string, nem JSON szám-tömb. `new Uint8Array(msg.data)` csendben 0 pontot ad — `atob()`-bal kell dekódolni.
2. **A LiDAR↔kamera transzformáció be van égetve a kódba**, nem élő TF-fel megy. A `ROSLIB.TFClient` a böngészőben csak a `/tf` topicot hallgatja; a robot statikus geometriája (URDF-ből) `/tf_static`-on megy, amit a kliens sosem kap meg. Fix mechanikai szerelésnél (LiDAR és kamera egymáshoz képest nem mozdul) egyszerűbb és megbízhatóbb a mért transzformációt egyszer lekérdezni (`rosrun tf tf_echo laser camera_depth_optical_frame`) és beégetni.
3. **Az IR kapcsoló szándékosan nincs bekötve a lapon** — lásd [07-ismert-hibak.md](07-ismert-hibak.md).

## Mit nem tud (még)

- Nem irányítja a motorokat vagy a kart — ez tisztán szenzor-megfigyelő irányítópult volt, az eredeti cél (motor/kar webes vezérlés) még nincs implementálva ezen a felületen.
- Az Astra RGB nem akart bekapcsolni egy vizsgálat közben — ez a hiba a session lezárásakor még nyitott volt, nem lett kivizsgálva.
