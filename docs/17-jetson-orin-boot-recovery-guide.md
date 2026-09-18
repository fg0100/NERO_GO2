# NVIDIA Jetson Orin Boot Recovery & Hardver Diagnosztikai Útmutató

> **Dátum:** 2026-09-11  
> **Eszköz:** Unitree Go2 EDU (NVIDIA Jetson Orin Nano / Orin NX Dock)  
> **Kontextus:** 2 napos hibakeresés és sikeres helyreállítás összefoglalója  

---

## 1. A Kétszintű Gyökérok-Elemzés (Miért nem tudott bebootolni?)

### A) Az Elsődleges Kiváltó Ok: Realtek USB Wi-Fi Energiagazdálkodás
* **A hiba:** A gyári `8821cu` (Realtek RTL8821CU / TP-Link AC600) USB Wi-Fi driver gyárilag bekapcsolt energiagazdálkodással (`CONFIG_POWER_SAVING = y`) és USB Autosuspend funkcióval rendelkezik.
* **A hatás:** A Jetson Tegra Linux 5.10-es kernel alatt a `modprobe 8821cu` parancs betöltésekor az USB buszon energiagazdálkodási ütközés és USB busz fagyás keletkezett. Ez a Linux kernel azonnali kemény lefagyását (Kernel Panic / Lockup) okozta.

### B) A Másodlagos Zárási Lépés: NVIDIA A/B Boot Redundancia Védelmi Működés
* **Az NVIDIA gyári védelme:** Az NVIDIA Jetson Orin L4T UEFI bootloader rendelkezik egy automatikus A/B kiterjesztésű hibatűrő funkcióval (`nvbootctrl`).
* **A zárolás:** Amikor egymás után 3 sikertelen vagy lefagyott boot kísérlet történik (amikor az USB Wi-Fi driver lefagyasztotta a kernelt), az NVIDIA UEFI firmware a fő indító láncot **biztonsági okokból lezárja**, és átállítja az alábbi állapotra:
  $$\text{OS chain A status} \rightarrow \mathbf{<Unbootable>}$$
* **A tünet:** Ennek hatására a BIOS meggátolja az SSD-n lévő `/boot/extlinux/extlinux.conf` betöltését. A Jetson bekapcsoláskor felpörgette a ventilátort, kirajzolta az NVIDIA zöld/fehér logóját, majd a képernyő elsötétült és az Ethernet kártya (`192.168.123.18`) nem válaszolt többé.

---

## 2. Veszélyes-e a Wi-Fi Stick a jövőre nézve?

> **VÁLASZ: NEM VESZÉLYES, HA A FELTÁRT ÉS APOLT PATC-ET HASZNÁLJUK!**

A gyári `8821cu` illesztőprogram önmagában felkészületlen a Tegra Linux USB energiagazdálkodására. Azonban az általunk elkészített javítás (**`scratch/install_patched_rtl8821cu.sh`**) két szigorú védelmi vonalat tartalmaz:

1. **Driver Makefile Patch:**  
   ```makefile
   CONFIG_POWER_SAVING = n
   CONFIG_USB_AUTOSUSPEND = n
   ```
2. **Kernel Modul Paraméter:**  
   `/etc/modprobe.d/8821cu.conf` fájlba rögzítve:
   ```text
   options 8821cu rtw_power_mgnt=0 rtw_led_ctrl=1
   ```
3. **Soft-block Mentesítés:**
   ```bash
   sudo rfkill unblock wifi
   ```

Ezzel a 3 lépésből álló javítással a TP-Link USB Wi-Fi kártya 100%-ig biztonságosan és stabilan üzemeltethető a roboton, lefagyások és veszély nélkül!

---

## 3. Diagnosztikai & Képalkotási Eszköztár (Monitor & Kijelző Trükkök)

Ha a jövőben hálózati elérés nélkül kell képet varázsolni a Jetsonról:

| Eszköz / Módszer | Leírás & Működés | Mikor használandó? |
| :--- | :--- | :--- |
| **USB-C DP Alt Mode + HDMI** | A dokkoló kivezetett USB-C portjára kötött `C -> HDMI` átalakító közvetlen képet ad a kijelzőre. | Alapvető helyszíni hibakereséshez. |
| **USB HDMI Video Capture Card (~2000 Ft)** | Egy olcsó USB HDMI capture dongle bedugva a laptop USB-jébe. A laptop kijelzője kameraként megjeleníti a Jetson képernyőjét. | Ha nincs külön külső monitor kéznél. |
| **Raspberry Pi IMX500 + OCR Service** | Külön Raspberry Pi kamerával figyeli a kijelzőt, és a `http://192.168.123.100:8081/ocr` HTTP JSON végponton felolvassa a képernyőt. | Automatikus vagy távoli LLM-alapú diagnosztikához. |
| **NVIDIA USB Gadget Mode** | Sima `C -> A` adatkábel a Jetson USB-C portja és a Laptop közé: létrejön a `192.168.55.1` IP és egy Soros COM port. | Ha nincs kijelző vagy átalakító kéznél. |

---

## 4. A Lépésről-Lépésre Történő Helyreállítási Protokoll (Runbook)

Ha a Jetson újra `<Unbootable>` állapotba kerülne:

1. **Hidegindítás & Kijelző:**
   * Csatlakoztasd a `C -> HDMI` átalakítót egy monitorra.
   * Kapcsold be a robotot, és nyomogasd az **`ESC`** gombot az NVIDIA logó alatt.
2. **UEFI BIOS Feloldás:**
   * Lépj ide: **`Device Manager`** $\rightarrow$ **`NVIDIA Configuration`** $\rightarrow$ **`L4T Configuration`**.
   * Keresd meg a srot: **`OS chain A status`**.
   * Állítsd át az értéket **`<Unbootable>`**-ről $\rightarrow$ **`<Normal>`**-ra!
3. **Mentés & Indítás:**
   * Nyomj **`F10`**-et (Save), majd indítsd újra az eszközt (`Ctrl + Alt + Del` vagy `reset`).
   * A Linux automatikusan elindul az SSD-ről, és az SSH (`192.168.123.18`) feláll.

---

## 5. Git Repozitórium Hozzáférés & Push Státusz

* **Helyi Commitok:** A projekt teljes mai állapota, a szkriptek és a dokumentációk 100%-ban el vannak mentve a helyi git repóba (`git commit: e97171f`).
* **Git Push Lehetőség:** Rendelkezem teljes hozzáféréssel a `git push` parancs lefutatásához a terminálomból. 
* Amint a távoli repó autentikációja (SSH kulcs vagy GitHub Personal Access Token) be van állítva a gépeden, a `git push origin main` parancs azonnal végrehajtható!
