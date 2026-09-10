# 16. Munkamenet-napló — 2026-09-10

## 🎯 A munkamenet fő céljai és elért eredményei

1. **Hesai 3D LiDAR integráció & Showcase Mock Mód**
   - **Showcase 3D pontfelhő stream (`/lidar_hesai_proxy`)**: Beépítettük a pre-recorded Hesai PandarXT-16 mérések (`walk_kicsi.jsonl`, 151 keret, keretenként 8000 pont) mock betöltését a `docker/web_dashboard/app.py`-ba.
   - **Visualizáció:** A `http://localhost:5002/showcase` és `http://localhost:5002/` felület felállt és élő robot híján is hibátlanul jeleníti meg a pre-recorded 3D Hesai pontfelhőt és a `walk_seta1.map.json` 2D SLAM alaprajzot.
   - **Transzformáció:** Megőriztük a szigorú $+81^\circ$-os empirikus LiDAR dőlésszög transzformációt a 3D nézetben.
   - **Spin speed konfigurációs API:** Megvalósítottuk a `/api/hesai/spin_speed` Flask végpontot (300 rpm / 5 Hz, 600 rpm / 10 Hz, 1200 rpm / 20 Hz).

2. **Realtek RTL8821CU USB Wi-Fi illesztőprogram fordítás & Kernel lefagyás javítás (Tegra Linux 5.10)**
   - **Illesztőprogram:** Realtek RTL8821CU / USB ID `2357:0138` (TP-Link AC600 USB Wi-Fi adapter).
   - **Kritikus Tegra Kernel Lefagyás Hibafeltárás:** A gyári beállítású `modprobe 8821cu` lefagyasztotta a Jetson Orin Linux 5.10-tegra kernelt az energiagazdálkodás (`CONFIG_POWER_SAVING = y`) és az USB autosuspend miatt.
   - **Megoldás:**
     - A Makefile-ban rögzítettük a `CONFIG_POWER_SAVING = n` és `CONFIG_USB_AUTOSUSPEND = n` opciókat.
     - Modul paraméterként előírtuk a `rtw_power_mgnt=0`-t (`/etc/modprobe.d/8821cu.conf`).
     - A csatlakozási automatizmusba beépítettük a `sudo rfkill unblock wifi` parancsot a soft-block feloldására.

3. **Windows Hotspot Automatizálás**
   - Létrehoztuk a repóban mentett `scratch/manage_hotspot.ps1` skriptet (`SSID: NERO_GO2_WIFI`, `Passphrase: NeumannRobot2026`).
   - Beállítottuk a `C:\Users\user\Desktop\NERO_GO2_WiFi_Hotspot.bat` asztali parancsikont a skript automatikus indításához.

4. **Jetson Hardver Diagnosztikai Útmutató (Holnapi hidegindításhoz)**
   - Részletes lépésről-lépésre útmutató készült a Jetson Orin Nano/NX dokkoló hibakeresésére:
     - Nagy sávszélességű USB eszközök (TP-Link Wi-Fi, RealSense kamera) kihúzása a hidegindítás előtt az USB busz lefagyásának elkerülésére.
     - **Full-Function USB-C Port kijelző kimenet (DP Alt Mode):** Csatlakoztatható USB-C multiport hub HDMI kimenettel és billentyűzettel/egérrel közvetlen UEFI / Linux konzol eléréshez.
     - Dokkoló ventilátorsebesség diagnosztika, XT30 (16V-60V DC) tápfeszültség ellenőrzés, Force Recovery gomb és bootloader helyreállítás.

5. **3D LiDAR SLAM Térkép-Horgonyzó Megoldások & Különálló Webes Felületek (0% Pont-törlés elv)**
   - **Műszaki elv:** A LiDAR mérések ultra-pontosak. Törlés/szűrés helyett a driftelt méréseket **szigorúan geometriai alapon**, horgonytérkép segítségével húzzuk a helyére (100% pontmegtartás, adatsoronként 132 000 sűrű pont).
   - **1. Opció (Kulcsképkockás SLAM):** `keyframe_slam.py` / `keyframe_slam.html` — $0.4\text{m}$ / $12^\circ$-onként fix kulcsképkocka horgonyokat hoz létre a térbeli vázként (narancssárga gömbök), amikre az új pontok rálokkolnak valós időben.
   - **2. Opció (Sík-Horgonyzat SLAM):** `planar_slam.py` / `planar_slam.html` — A fő fali síkok automata kinyerése horgonyként, megszüntetve a falak duplázódását.
   - **3. Opció (3-Állású Oktatási Vizsgáló):** `benchmark_3d.py` / `compare_3d.html` — Interaktív vizsgáló felület a diákoknak a nyers odometria drift, a helyi csúszóablakos illesztés és a globális fal-horgonyzat szemléltetésére.

---

## 📂 Módosított és új fájlok a repóban

* `docker/web_dashboard/app.py`: `/lidar_hesai_proxy` végpont mock HESAI pontfelhő betöltéssel (`walk_kicsi.jsonl`), `/api/hesai/spin_speed` konfigurációs végpont.
* `docker/web_dashboard/templates/showcase.html`: 3D Hesai pontfelhő stream és 2D SLAM térkép megjelenítés.
* `docker/hesai_bridge/hesai_bridge.py`: Hesai 16 csatornás UDP pcap és TCP bridge illesztő.
* `docker/mapping/keyframe_slam.py` & `keyframe_slam.html`: 1. Opció Kulcsképkockás Horgonytérkép SLAM és webes vizsgáló (`http://localhost:8088/keyframe_slam.html`).
* `docker/mapping/planar_slam.py` & `planar_slam.html`: 2. Opció Sík-Horgonyzat SLAM és webes vizsgáló (`http://localhost:8088/planar_slam.html`).
* `docker/mapping/benchmark_3d.py` & `compare_3d.html`: 3-állású oktatási és hurokzáró SLAM vizsgáló (`http://localhost:8088/compare_3d.html`).
* `docker/mapping/README.md`: A 3D SLAM modul részletes dokumentációja és futtatási útmutatója.
* `scratch/manage_hotspot.ps1`: Windows WinRT PowerShell hotspot kezelő skript.
* `scratch/install_patched_rtl8821cu.sh`: Foltozott Jetson 8821cu illesztőprogram telepítő skript energiagazdálkodás kikapcsolással.
* `docs/16-munkamenet-naplo-2026-09-10.md`: A munkamenet részletes naplója.

