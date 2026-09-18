# Saját projekt #3 — kézi vezérlés (bázis + kar)

**Építve: 2026-09-18, robot offline (SSH nem elérhető) — semmi ebből nem lett élő roboton tesztelve.** Célja: a meglévő, csak-megfigyelő [05-sajat-projekt-iranyitopult.md](05-sajat-projekt-iranyitopult.md) irányítópult kiegészítése tényleges bázis- és kar-vezérléssel, ugyanazzal a biztonsági doktrínával, mint amit a testvér-repóban ([NERO_GO2](../) fő projekt, Go2 négylábú) a `docker/web_dashboard/joint_safety.py` + `lowcmd_sender.py` mock/real-split párra építettünk.

**FONTOS:** ez a robot **nem** a Go2 négylábú. Mecanum-alváz + 4 DOF kar, ROS1 Noetic (nem DDS/LowCmd). A Go2 ízület-számokat, sebesség-plafonokat sehol nem vettük át — minden itt szereplő szám ezen a roboton, ehhez a hajtáshoz lett (óvatosan) kitalálva, vagy explicit PLACEHOLDER-ként jelölve.

## Mi épült

| Komponens | Fájl | Állapot |
|---|---|---|
| Bázis (mecanum) Twist-építő + rate-limiter | [scripts/xavier_control/base_drive.py](../scripts/xavier_control/base_drive.py) | **valós-képes** — de csak ha valaki ténylegesen bekötné egy publish hívásba; a modul maga csak dict-eket épít |
| Kar/gripper mock sender | [scripts/xavier_control/arm_control.py](../scripts/xavier_control/arm_control.py) | **MOCK-ONLY** — szándékosan nem tud valós ROS API-t hívni |
| Webes vezérlőpult | [scripts/control_panel.html](../scripts/control_panel.html) | bázis: valós `/cmd_vel` publish, de ÉLESÍTÉS-kapu mögött, alapból KI; kar: mindig szimuláció |
| Unit tesztek | `scripts/xavier_control/tests/test_base_drive.py`, `test_arm_control.py` | 25/25 zöld (`python -m pytest tests/` a `xavier_control/` mappában) |

## Valós-képes vs. mock-only — és miért ez a különbség

**Bázis-vezérlés (`/cmd_vel`, `geometry_msgs/Twist`) valós-képesnek számít**, mert:
- Ez a Wheeltec `turn_on_wheeltec_robot` alap-driver saját, jól dokumentált konvenciója, amit a gyári `wheeltec_joy_control` package is használ.
- Egy Twist (linear.x/y, angular.z) formátumhoz nem kell ízület-szintű geometriai adat, ami hiányzik — csak sebesség-parancs.

**A kar mock-only marad**, mert:
- A `mini_mec_four_arm_moveit_config` valós ízület-határai, topic-nevei és üzenet-mezői **nincsenek leolvasva** a robot URDF/SRDF-jéből vagy `rostopic`/`rosservice` hívással — a robot ezen a sessionön nem volt elérhető.
- Egy 4 DOF karnál egy rossz ízület-határ vagy topic-név a gripper/bázis/tartott tárgy ütközését okozhatja — ez nem olyan kockázat, amit "óvatos becsléssel" el lehet fedezni, mint egy lassú bázis-sebességnél.
- Amíg nincs valós szám, minden ízület-limit ebben a repóban **PLACEHOLDER** (lásd `arm_control.py` `PLACEHOLDER_JOINT_LIMITS_RAD`), és a modul szerkezetileg (import-szint, AST-teszt) sem tud valós ROS API-t elérni.

## A biztonsági plafonok pontos értékei és miért ilyenek

`scripts/xavier_control/base_drive.py`:

| Paraméter | Érték | Eredet |
|---|---|---|
| `MAX_LINEAR_MPS` | 0.15 m/s | **Óvatos alapérték, NEM mért hardver-plafon.** Nincs adatlap, nincs mért csúcssebesség ezen a példányon. |
| `MAX_ANGULAR_RADPS` | 0.3 rad/s | Ugyanaz — óvatos becslés, nem mérés. |
| `MAX_LINEAR_ACCEL_MPS_PER_TICK` / `MAX_ANGULAR_ACCEL_RADPS_PER_TICK` | 0.03 / 0.06 (tick ≈ 1/20 s referenciánál) | Cél: ~0.5s alatt érje el a max sebességet egy tartott gombnál, ne egy UI-kattintásra ugorjon oda azonnal. |

Ha az első élő teszten a robot gyorsabban mozog a vártnál ezekkel az értékekkel, **csökkentsd tovább** ezeket a számokat — ne emeld feljebb egy sikeres teszt után anélkül, hogy tudnád, mi a valós fizikai plafon.

`scripts/xavier_control/arm_control.py` `PLACEHOLDER_JOINT_LIMITS_RAD`: kitalált, kis 4 DOF oktatási karra jellemző radián-tartományok, **nem** ebből a robotból olvasva. Ezeket a valós `mini_mec_four_arm_moveit_config` URDF/SRDF-jéből (vagy élő `rosparam get /robot_description`-ből) kell lecserélni, mielőtt bármilyen valós kar-küldés bekapcsolna.

## Első élő teszt — lépésről lépésre (amikor a robot legközelebb elérhető)

Ne kezdd el ezt a listát, amíg nincs valaki a robot közelében, aki fizikailag el tudja kapcsolni az áramot (tápkapcsoló/battery), és amíg nincs meg a `rostopic`-os megerősítés.

1. **SSH-kapcsolat + roscore él.** `ssh -i ~/.ssh/pickerbot_mini wheeltec@192.168.123.50`, ellenőrizd, hogy `roscore` fut (vagy indítsd el `scripts/start_feeds.sh`-val, ami már úgyis elindítja).
2. **`/cmd_vel` MEGLÉTÉNEK ellenőrzése ELŐSZÖR, mielőtt bármit küldenél:**
   ```bash
   rostopic list | grep cmd_vel
   rostopic info /cmd_vel
   ```
   Ha a topic neve vagy típusa más, mint `geometry_msgs/Twist` a `/cmd_vel` néven, **állj meg** — `base_drive.py` és `control_panel.html` mindkettő ezt a nevet/típust feltételezi, nem megerősítve. Ha eltér, előbb ezt kell javítani a kódban, nem ráerőltetni a robotra.
3. **Fizikai E-stop/kéz a tápkapcsolón.** Valaki álljon a robot mellett úgy, hogy egy mozdulattal le tudja kapcsolni az áramot (barrel jack / battery kapcsoló), mielőtt az első parancs kimegy.
4. **Nyisd meg `scripts/control_panel.html`-t** `python -m http.server 8901`-ről (ne `file://`), és ellenőrizd, hogy a `globalStatus` "rosbridge: csatlakozva"-t mutat.
5. **NE élesíts azonnal.** Előbb figyeld pár másodpercig a naplót MOCK módban (élesítés nélkül) — minden gombnyomás "MOCK (nincs élesítve)" sort ír, ellenőrizd, hogy az irányok logikusak (előre=x+, balra strafe=y+, stb.), mielőtt bármi kimenne a robotra.
6. **Élesítés minimális sebességgel.** Kattints az ÉLESÍTÉS gombra (megerősítő dialógus jön), majd **rövid, kis nyomásokkal** próbáld ki egyenként az irányokat — ne tartsd lenyomva hosszan az első próbánál.
7. **E-STOP gomb / szóköz-billentyű reflex.** Az E-stop gomb azonnal nulla Twist-et küld és leélesít — próbáld ki ezt is tudatosan, mielőtt bármilyen komolyabb mozgást kérnél.
8. **Karvezérlés valós bekapcsolása NEM ezen a listán van.** A kar addig marad szimuláció-only, amíg valaki nem olvassa le a valós ízület-határokat a `mini_mec_four_arm_moveit_config`-ból (vagy élő `rosparam`/`rostopic`/`rosservice` hívásokkal a running MoveIt node-okról), és be nem írja azokat `arm_control.py`-ba a `PLACEHOLDER` jelölés törlésével együtt — külön, tudatos lépésként, nem ennek a dokumentumnak a részeként.

## Amit ez a projekt NEM csinál

- Nem hívja soha az `/camera/toggle_ir` service-t — lásd [07-ismert-hibak.md](07-ismert-hibak.md).
- Nem tesz semmilyen feltételezést a robotkar valós topic-nevéről, üzenettípusáról vagy ízület-sorrendjéről — minden ilyen `arm_control.py`-ban PLACEHOLDER-ként van jelölve.
- Nem indít semmilyen SSH-kapcsolatot magától a robot felé (ezt a session sem tette, mert a robot offline volt).

## Nyitott kérdés

`/cmd_vel` léte/típusa **ezen a konkrét robotpéldányon** ebben a sessionben nem volt megerősíthető (a robot nem válaszolt SSH-ra). Lásd a fenti "Első élő teszt" 2. lépését — ez az egyetlen dolog, amit élő roboton MINDENKÉPPEN meg kell nézni, mielőtt a bázis-vezérlést élesítve használnánk.
