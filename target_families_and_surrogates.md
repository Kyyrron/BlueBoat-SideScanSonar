# Target Families and Orderable Surrogates
 
## Filtering the ports/canals litter inventory into a buyable test-target set for surface-platform SSS
 
*Companion to `seabed_objects_ports_canals_15cm.md`. Compiled August 2026.*
*Purpose: decide which real seabed objects are worth simulating, group them into acoustically
meaningful families, and give a concrete shopping list of Japanese-orderable stand-ins.*
 
---
 
## Table of contents
 
1. [How the list was filtered](#1-how-the-list-was-filtered)
2. [Filtering result — what is kept, dropped and deferred](#2-filtering-result--what-is-kept-dropped-and-deferred)
3. [The nine target families](#3-the-nine-target-families)
   - [F1 — Upright rigid box](#f1--upright-rigid-box)
   - [F2 — Large upright cylinder](#f2--large-upright-cylinder)
   - [F3 — Dense solid block](#f3--dense-solid-block)
   - [F4 — Open-frame / skeletal](#f4--open-frame--skeletal)
   - [F5 — Elongated linear rigid](#f5--elongated-linear-rigid)
   - [F6 — Tapered / conical](#f6--tapered--conical)
   - [F7 — Toroid and low-profile compliant](#f7--toroid-and-low-profile-compliant)
   - [F8 — Tangled compliant mass](#f8--tangled-compliant-mass)
   - [F9 — Small hard threshold objects](#f9--small-hard-threshold-objects)
4. [Matched pairs — the controlled contrasts worth building in](#4-matched-pairs--the-controlled-contrasts-worth-building-in)
5. [Recommended purchase tiers](#5-recommended-purchase-tiers)
6. [Rigging, ballasting, recovery, permissions](#6-rigging-ballasting-recovery-permissions)
7. [Caveats on the surrogate mapping](#7-caveats-on-the-surrogate-mapping)
---
 
## 1. How the list was filtered
 
Four filters were applied, in this order. Nothing here relies on the `h_min ≈ 0.026·H` criterion or
any other unvalidated envelope claim — those are hypotheses to be *tested* with these objects, not
inputs to choosing them.
 
### 1.1 Geometric access filter (the one that removes the most)
 
The sonar cannot be placed arbitrarily close to a target. With a hard near-field floor around
9–10 m slant range and altitude fixed at water depth, the vehicle needs roughly 9–10 m of
*horizontal* standoff, on both sides if lines are to be run properly. In practice the water body must
be **≳ 25–30 m wide** with clear water either side of the track.
 
Consequence: **the entire canal / urban-river / 用水路 section of the source list is geometrically
inaccessible to this platform**, however rich it is in objects. Amsterdam-style canals (~15–25 m),
Dōtonbori, and irrigation channels are all too narrow to image with a hull-mounted 450 kHz SSS at a
usable range. Those object classes are only relevant where the *same object type* also occurs in an
open port basin — which most of them do (bicycles, trolleys, cones, pipe, blocks, bottles). So the
canal list is kept as an **object-type source**, not as a site type.
 
**Kept settings:** fishing-harbour basins, marina outer basins, port basins, quay aprons, nearshore
anchorages — the 2–15 m band in §3 of the source document, which matches the Kasaoka / Shiraishi-jima
/ Dōkai Bay operating envelope.
 
**Dropped settings:** canals, urban river beds, irrigation channels, and anything reached only by
offshore trawl (the MOE bay surveys, Kuroda et al. offshore densities, all abyssal references).
 
### 1.2 Depth-band filter
 
| Band | Objects | Verdict |
|---|---|---|
| Intertidal / < 2 m | Quay-toe debris, beach-adjacent litter | Too shallow — hull draft plus near-field floor make this unusable; also swath collapses |
| **2–8 m — the working band** | Fishing-port basins, marina basins, inner harbour aprons; most of §3.1 and §3.2 of the source list | **Primary.** Also the band with the largest tidal depth sweep at Kasaoka (~3 m), which is exactly the covariate the design wants |
| 8–15 m | Commercial port basins, turning basins, deeper anchorages | Secondary — good for contrast runs, but access and permission are harder |
| > 15 m | Offshore / bay-floor debris | Out of scope |
 
### 1.3 Size filter
 
Working rule, deliberately conservative and independent of any predicted envelope:
 
- **Along-track extent ≥ 30 cm** for a *primary* target. At 25 m slant range the along-track cell is
  around 0.2 m, so 30 cm is only about 1.5 cells — this is already an aggressive floor, not a safe
  one.
- **30–50 cm objects are threshold probes**, not detection targets. Expect them to be marginal.
- **≥ 20 cm of vertical relief** preferred for anything expected to cast usable shadow.
- **20–30 cm objects retained only as deliberate near-floor controls** (cans, bottles) — their job
  is to fail informatively.
This drops from the source list: all fragments, 350 mL cans, cup-noodle containers, bento boxes,
footwear, sports balls, helmets, flowerpots under 30 cm, and every film/bag/wrapper category (already
excluded upstream).
 
### 1.4 Practicality filter (deployment and recovery from a small craft)
 
- **Must be liftable by two people from a RIB / small boat** — practical ceiling around 25–30 kg
  wet, and it must fit through a hatch or over a gunwale.
- **Must sink and stay put in tidal current** — hollow items need ballast, which is itself an
  acoustic decision (see §6).
- **Must be recoverable in full** — every object leaves the water at end of day. Nothing is
  abandoned, both for legal reasons and because an unrecovered target contaminates later runs.
- **Must be cheap enough to lose one.** Anything above roughly ¥10,000 per unit is a bad bet.
This drops: sunken small craft, cars, refrigerators and washing machines, outboard motors, mooring
blocks over ~30 kg, and full 200 L drums (the drum is kept, but as an *empty* shell — 23 kg — and
only if a lift point is available).
 
---
 
## 2. Filtering result — what is kept, dropped and deferred
 
### 2.1 Kept as primary target classes
 
| Source-list object | Setting / depth | Size | Family |
|---|---|---|---|
| 一斗缶 (18 L square tin) | Port basin, quayside, 2–8 m | 24 × 24 × 35 cm | F1 |
| Fish crates (プラ製魚箱), EPS fish boxes | Fishing harbour, 2–8 m | ~50 × 35 × 20–25 cm | F1 |
| Lead-acid batteries | Port basin | 24 × 17 × 20 cm | F1 |
| Buckets, tubs, wash basins | Port + quayside | 25–40 cm dia. × 25–35 cm | F1 / F2 |
| 20 L polytanks (ポリタンク) | Port basin, drifting-then-sinking | 34 × 24 × 46 cm | F1 |
| Steel drums (200 L) | Port basin, industrial quays | 88 cm × 58 cm dia. | F2 |
| Fire extinguishers, gas cylinders | Quayside | 50 cm / 60–120 cm | F2 |
| Plastic and EPS buoys / floats | Fishing harbour | 20–60 cm dia. | F2 |
| Octopus pots (タコ壺) | Fishing harbour, western Japan | 25–30 cm × 20 cm dia. | F2 |
| Concrete rubble, blocks, bricks | Port basin, quay toe | 39 × 19 × 12 cm | F3 |
| Anchors, chain piles, mooring blocks | Port basin, permanent | 40–100 cm | F3 |
| Bicycles | Urban quays and city harbours | 170 × 60 × 100 cm | F4 |
| Shopping baskets / trolleys | Urban quays | 40 × 30 × 25 cm / 100 × 60 × 100 cm | F4 |
| Crab / whelk pots and traps | Fishing harbour | 60–120 × 40–60 cm | F4 |
| Furniture (chairs, stools) | Quayside | 40–90 cm | F4 |
| Wire drums, scaffolding, pipe | Working quays | 1–4 m / 40–80 cm dia. | F4 / F5 |
| Conger-eel tube traps (アナゴ筒) | Fishing harbour | 60–100 × 10 cm dia. | F5 |
| Wooden pallets and dunnage | Cargo quays | 110 × 110 × 14 cm | F5 |
| Traffic cones, bollards, barricades | Quayside, promenade | 70 cm / 80–120 cm | F6 |
| Tyres used as quay fenders | Fishing harbour, very common | 60–70 cm dia. × 20 cm | F7 |
| Rubber boat fenders | Marina | 40–70 × 15–25 cm dia. | F7 |
| Rope coils / mooring line bundles | Marina, harbour — the highest-frequency class | 30–100 cm across | F8 |
| Net bundles, "net balls", trawl offcuts | Fishing harbour | 0.5–3 m tangled | F8 |
| Glass bottles (一升瓶, 大瓶) | All settings, sink immediately | 31–40 cm | F9 |
| PET bottles (2 L) | All settings, top item in Osaka Bay | 31 × 9 cm dia. | F9 |
 
### 2.2 Dropped
 
| Object | Reason |
|---|---|
| All canal / 用水路 site classes | Geometric access — basin too narrow for 10 m standoff |
| Sunken small craft, pontoons, cars | Unrecoverable; also a one-off opportunistic find, not a controllable target |
| Home appliances, furniture over ~90 cm | Weight and recovery; washing machine ≈ F1 acoustically anyway, so nothing is lost |
| Outboard motors, propellers, engine parts | Cost, weight, oil contamination risk |
| Vinyl umbrellas | Below the size floor in every dimension that matters; thin ribs, near-zero cross-section |
| Footwear, sports balls, helmets, small flowerpots | Below the 30 cm working floor |
| 350 mL / 500 mL cans, cup-noodle containers | Below floor; the 2 L PET bottle already covers the small-hard probe role |
| Prams, wheelchairs, suitcases, safes, filing cabinets | Canal-only in the source data; acoustically already covered by F1 and F4 |
| All film, bag, wrapper, sheet, textile categories | Excluded upstream by the shape filter and correctly so |
 
### 2.3 Deferred / opportunistic
 
Objects worth **labelling if they show up in real survey data** but not worth deploying: sunken
dinghies, chain piles, dredging spoil, quay-wall rubble aprons, agricultural gear. These belong in
the clutter and false-positive analysis, not in the controlled target set.
 
---
 
## 3. The nine target families
 
Families are defined by **acoustic-geometric class**, not by litter taxonomy — because two objects
that look nothing alike in a litter inventory (a battery and a fish crate) present the same thing to
the sonar, while two objects in the same litter row (a solid-wall crate and a mesh crate) do not.
 
Each family below lists what it contains from the filtered set, what it tests, and orderable
surrogates. Prices are indicative and pre-shipping.
 
---
 
### F1 — Upright rigid box
 
**Contains:** 一斗缶, fish crates, EPS fish boxes, 20 L polytanks, lead-acid batteries, shopping
baskets (solid), suitcases, small appliances.
 
**What it tests.** Flat vertical faces of 20–50 cm. This is the *mirror* class: near broadside the
face returns a strong specular flash; a few degrees off, the return collapses. Expect the sharpest
aspect dependence of any family, and therefore the most direct test of whether multi-aspect revisit
recovers targets that single-pass coverage drops. Vertical relief of 25–45 cm also makes this the
family most likely to produce a usable shadow, so it doubles as the shadow-vs-highlight discriminator.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **一斗缶 18 L, empty, unprinted** — 238 × 238 × 349 mm, tinplate, ~1.14 kg | [Amazon.co.jp — ビー・エヌ 一斗缶 18 L 生地缶](https://www.amazon.co.jp/%E3%83%93%E3%83%BC%E3%83%BB%E3%82%A8%E3%83%8C-%E4%B8%80%E6%96%97%E7%BC%B6-18%E3%83%AA%E3%83%83%E3%83%88%E3%83%AB%E7%BC%B6-%E7%94%9F%E5%9C%B0%E7%BC%B6/dp/B09HWZFHVQ) (~¥1,300–1,800) | Not a surrogate at all — this **is** the real object, a distinctly Japanese port-litter class, at exact JIS dimensions. Steel shell, four flat faces, 35 cm relief. Cheap enough to buy six and vary orientation. First thing to order. |
| Same, lab-grade alternative — アズワン 18L, 235 × 235 × 340 mm, epoxy-lined | [Amazon.co.jp — アズワン 1-3798-01](https://www.amazon.co.jp/%E3%82%A2%E3%82%BA%E3%83%AF%E3%83%B3-As-One-18L-No-40%E5%86%85%E9%9D%A2%E3%82%A8%E3%83%9D%E3%82%AD%E3%82%B7%E3%82%B3%E3%83%BC%E3%83%88%E7%BC%B6/dp/B01N1TYVWB) (~¥1,760) | Same geometry with a documented spec sheet, useful if you want a traceable dimension in the paper. |
| **Solid-wall folding container 50 L** — 530 × 366 × 320 mm, PP | [Amazon.co.jp — 松本産業 折りたたみコンテナ 50 L (50B)](https://www.amazon.co.jp/%E6%9D%BE%E6%9C%AC%E7%94%A3%E6%A5%AD-%E6%A5%AD%E5%8B%99%E7%94%A8-%E6%8A%98%E3%82%8A%E3%81%9F%E3%81%9F%E3%81%BF%E3%82%B3%E3%83%B3%E3%83%86%E3%83%8A-%E3%83%95%E3%82%BF%E7%84%A1%E3%81%97-50B/dp/B087WWWY58) (~¥2,000) | Direct stand-in for プラ製魚箱 / fish crate — the same footprint and the same polypropylene. Folds flat for transport to the site, which matters when you are carrying eight targets in a car. Pairs with the 一斗缶 as a **matched shape, contrasting material** test (see §4). |
| Bulk 50 L box (rigid) — 160 kg rated, handles | [Amazon.co.jp — 取っ手付きコンテナボックス 50 L](https://www.amazon.co.jp/%E5%8F%96%E3%81%A3%E6%89%8B%E4%BB%98%E3%81%8D-160kg-%E5%8F%8E%E7%B4%8D%E3%83%9C%E3%83%83%E3%82%AF%E3%82%B9-%E6%8C%81%E3%81%A1%E9%81%8B%E3%81%B3%E7%B0%A1%E5%8D%98-%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%B3%E3%83%9B%E3%83%AF%E3%82%A4%E3%83%88/dp/B0BTSBG828) | Thicker wall than the folding type; survives repeated deployment/recovery better. Integral handles are lift and rigging points. |
 
**Note.** A sealed air-filled 一斗缶 is acoustically the brightest thing on this list (steel/air
interface) but will not sink. Externally ballasting with a concrete block on a short strop preserves
the air fill; flooding the can does not. At 3–8 m the external pressure is only 0.3–0.8 bar, but thin
tinplate can still buckle — inspect after each dive and treat a buckled can as a different target.
 
---
 
### F2 — Large upright cylinder
 
**Contains:** 200 L steel drums, fire extinguishers, gas cylinders, pail cans, buckets, buoys and
floats, octopus pots.
 
**What it tests.** The curved vertical surface gives a return that is **broad in azimuth but weak per
unit area** — the opposite trade to F1. In principle a cylinder should be the least aspect-dependent
rigid target in the set, which makes it the *control* against which F1's and F4's aspect behaviour is
measured. If cylinders also turn out aspect-critical, the aspect argument needs rethinking.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **Steel pail can 20 L** — φ300 top / φ275 bottom × 370 mm | [Amazon.co.jp — ペール缶本体 20 L シルバー](https://www.amazon.co.jp/%E3%82%B5%E3%83%BC%E3%83%89%E3%83%BB%E3%82%B9%E3%83%86%E3%83%83%E3%83%97%E6%A0%AA%E5%BC%8F%E4%BC%9A%E7%A4%BE-%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6%E6%9C%AC%E4%BD%93-20%EF%BC%AC-%E3%82%B7%E3%83%AB%E3%83%90%E3%83%BC/dp/B007PBU1E2) or [ニス引きペール缶 20 L 870-54](https://www.amazon.co.jp/%E3%83%8E%E3%83%BC%E3%83%96%E3%83%A9%E3%83%B3%E3%83%89%E5%93%81-%E3%83%8B%E3%82%B9%E5%BC%95%E3%81%8D%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6-20L-%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6%E3%81%AE%E3%81%BF-870-54/dp/B08JQ5KV1H) (~¥1,500) | A scaled steel drum: same material, same shape, 1/10 the mass, one-person handling. Stands upright or lies down, giving two very different targets from one purchase. Buy several — [5-can set](https://www.amazon.co.jp/%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6-%E7%A9%BA%E7%BC%B6-%E3%82%AA%E3%82%A4%E3%83%AB%E7%BC%B6-20L-5%E7%BC%B6%E3%82%BB%E3%83%83%E3%83%88/dp/B0DZHBTZN4). |
| **Plastic pail 20 L** — same envelope, PP/PE | [Amazon.co.jp — プラスチックペール缶 20 L](https://www.amazon.co.jp/%E3%83%97%E3%83%A9%E3%82%B9%E3%83%81%E3%83%83%E3%82%AF%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6-20L-%E5%86%8D%E7%94%9F%E5%AE%B9%E5%99%A8-%E5%8F%96%E3%81%A3%E6%89%8B%E4%BB%98%E3%81%8D-%E3%83%87%E3%82%B6%E3%82%A4%E3%83%B3%E9%81%B8%E6%8A%9E%E4%B8%8D%E5%8F%AF/dp/B085X2D1SM) (~¥900–1,500) | The single cleanest **material-contrast pair** available: identical geometry, steel vs plastic, ¥2,500 for the pair. Directly reproduces the USNA aluminium-vs-LDPE result in your own water. |
| **200 L open-top steel drum** — 585 mm dia. × 890 mm, 23.2 kg | [MonotaRO — 空ドラム缶 200 L](https://www.monotaro.com/s/q-%E7%A9%BA%E3%83%89%E3%83%A9%E3%83%A0%E7%BC%B6%20200l/) (~¥10,000–15,000) | The real object from the source list, at real dimensions. Heavy — deploy once, image it for a whole tidal cycle, recover with a davit or a lifting strop. Best single "unmissable" reference target for calibrating a run. |
| **ABC powder fire extinguisher, 10-型** — ~440–490 mm high, φ127–150 mm, ~4–5 kg | [Amazon.co.jp — 日本ドライ PAN-10AG](https://www.amazon.co.jp/%E6%97%A5%E6%9C%AC%E3%83%89%E3%83%A9%E3%82%A4-%E8%87%AA%E5%8B%95%E8%BB%8A%E7%94%A8%E3%83%BBABC%E7%B2%89%E6%9C%AB%E5%8A%A0%E5%9C%A7%E5%BC%8F10%E5%9E%8B%E6%B6%88%E7%81%AB%E5%99%A8-PAN-10AG-%E2%85%A0/dp/B0018AXZG2), or [MonotaRO — 消火器 ABC 10型](https://www.monotaro.com/k/store/%E6%B6%88%E7%81%AB%E5%99%A8%20ABC%2010%E5%9E%8B/) (~¥4,000–7,000) | Again the real object. Dense steel bottle, self-sinking without ballast, awkward small diameter — a good "small but bright" probe near the along-track resolution limit. Buy an expired/discharged unit if a local supplier will part with one. |
| **Octopus pot (タコ壺)** — 25–30 cm, plastic or ceramic, cement-ballastable | [MonotaRO — 蛸壺 category](https://www.monotaro.com/k/store/%E8%9B%B8%E5%A3%BA/) · [せんぐ屋 — たこつぼ（重し入り）](https://www.senguya.jp/SHOP/takotubo_01.html) | Region-appropriate for the Seto Inland Sea and genuinely present on those seabeds. The せんぐ屋 version ships with ballast already cast in, so it is drop-and-go. Also a natural rough-surface, partially-hollow contrast to the smooth pail can. |
| Water bucket / tub, 25–40 cm | Any home centre; [Amazon — ふた付バケツ #10, φ28 × 27.3 cm](https://www.amazon.co.jp/%E3%83%97%E3%83%A9%E3%82%B9%E3%83%81%E3%83%83%E3%82%AF%E3%83%9A%E3%83%BC%E3%83%AB%E7%BC%B6-20L-%E5%86%8D%E7%94%9F%E5%AE%B9%E5%99%A8-%E5%8F%96%E3%81%A3%E6%89%8B%E4%BB%98%E3%81%8D-%E3%83%87%E3%82%B6%E3%82%A4%E3%83%B3%E9%81%B8%E6%8A%9E%E4%B8%8D%E5%8F%AF/dp/B085X2D1SM) listing page carries several | Cheapest possible near-threshold cylinder. Expect it to be marginal; that is the point. |
 
---
 
### F3 — Dense solid block
 
**Contains:** concrete blocks, bricks, rubble, mooring blocks, anchors.
 
**What it tests.** High impedance contrast, rough surface, no internal structure, no air. This should
be the **easiest** family to detect and the least aspect-sensitive — the reference "if we cannot see
this, the run is bad" target. It also doubles as universal ballast for every other family, so it is
worth over-ordering.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **JIS C種 concrete block, 390 × 190 × 100 mm, ~9.7 kg** | [Amazon.co.jp — コンクリートブロック 基本 4個セット](https://www.amazon.co.jp/%E3%82%B3%E3%83%B3%E3%82%AF%E3%83%AA%E3%83%BC%E3%83%88%E3%83%96%E3%83%AD%E3%83%83%E3%82%AF-%E5%9F%BA%E6%9C%AC-4%E5%80%8B%E3%82%BB%E3%83%83%E3%83%88-JIS%E5%B7%A5%E5%A0%B4%E8%A3%BD%E5%93%81-%E5%8E%9A%E3%81%BF100mm%C3%97%E6%A8%AA390mm%C3%97%E7%B8%A6190mm/dp/B089GLCTCP) (~¥2,000/4) | Exactly the object in the source list at exactly the quoted dimensions. Two hollow cores give it internal structure a solid brick lacks — realistic for real rubble. Stacking two or three builds a taller block with the same footprint, which is a free height sweep. |
| Same in 120 mm thickness, ~10.9–12 kg | [Rakuten — 平野ブロック 390 × 190 × 120](https://item.rakuten.co.jp/hirano-block/1000150012/) · [ロイモール — 重量ブロック C種 12 cm](https://www3.roymall.jp/shop/g/grhc1-035104/) | Slightly deeper, otherwise identical — a controlled 2 cm relief step if you want one. |
| Bulk ballast, 10-block pack | Same Amazon / Rakuten listings as above, sold in 2/4/10 packs | Buy ~15 blocks total. Every hollow target in F1, F2, F6 and F7 needs one or two, and blocks are the cheapest thing here per kilogram. |
 
---
 
### F4 — Open-frame / skeletal
 
**Contains:** bicycles, shopping trolleys and baskets (wire), crab and whelk pots, chairs and stools,
scaffolding assemblies, net frames, wire drums.
 
**What it tests.** **This is the family that produced the July wireframe-cube failure**, and the most
scientifically interesting one. Silhouette fill fraction is low, so the shadow is diluted; the return
is a sparse set of thin-member specular flashes whose geometry changes completely with aspect. If
multi-aspect revisit has a detection benefit anywhere, it is here. It is also the family most likely
to defeat a YOLO detector trained on AUV shipwreck imagery.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **Mesh folding container 50 L** — 530 × 366 × 320 mm, open lattice walls | [Amazon.co.jp — 松本産業 brand store, model 50ABL メッシュ](https://www.amazon.co.jp/stores/%E6%9D%BE%E6%9C%AC%E7%94%A3%E6%A5%AD/page/98BB7F14-2B10-41BE-9A7D-ABE7C8287CA5) (~¥2,000) | The single most valuable purchase on this page. It is **dimensionally identical to the solid-wall 50B in F1** but with lattice walls, giving a controlled fill-fraction pair for the same footprint and material — a clean, publishable test of the fill-fraction hypothesis, for about ¥4,000 total. |
| Transparent skeleton container — TRUSCO スケルコン 50 L, 530 × 366 × 336 mm, 2.28 kg | [kakaku.com — スケルコン TSK-C50B](https://search.kakaku.com/%E3%82%B3%E3%83%B3%E3%83%86%E3%83%8A%2050l/) (~¥3,000) | Third point on the same fill-fraction axis. |
| **Second-hand bicycle** (frame + wheels) | Local recycle shop, Jimoty, or Mercari — *do not* order new; a ¥3,000–5,000 junk bike is the right purchase | Very-high-frequency object in the source list and the archetypal open frame: two large thin rings, a thin-tube triangle, one dense hub cluster. Steel frame preferred over aluminium. Needs a block or two to hold position. Recovery by rope through the frame is easy. |
| **Crab / whelk pot, folding wire trap** | [MonotaRO — 雑漁具 (漁網/漁具) category](https://www.monotaro.com/s/c-135814/) | Real fishing-harbour object, coated wire frame, sold with enough weight to sit stably on the bottom. Cheap, stackable, several can be deployed in one trip. |
| Steel folding chair / stool | Any home centre or Amazon (search 「パイプ椅子」) | Covers the furniture row. Thin-tube frame plus one flat plate: a hybrid of F4 and F1 in a single object, useful for testing what a detector latches onto. |
| Steel scaffold tube + clamps, assembled into a 1 m cube | See F5 for the tube link; clamps via [MonotaRO — 単管パイプ 48.6](https://www.monotaro.com/s/q-%E5%8D%98%E7%AE%A1%E3%83%91%E3%82%A4%E3%83%97%2048.6/) | Rebuilds the July wireframe cube deliberately, in steel rather than whatever the original was, so the failure can be reproduced and attributed rather than assumed. Disassembles for transport. |
 
---
 
### F5 — Elongated linear rigid
 
**Contains:** PVC and steel pipe, rebar, scaffold poles, guardrail sections, timber and sleepers,
pallets, conger-eel tube traps (アナゴ筒), garden-hose reels.
 
**What it tests.** The narrow-specular-lobe case. A long straight edge should be brilliant at
broadside and near-invisible elsewhere — the most extreme aspect window in the whole set, and the
cleanest possible test of the aspect argument, because orientation on the seabed is exactly
controllable (lay it along a known bearing with RTK at both ends).
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **PVC pipe VU100, 1 m** — 114 mm OD, ~1 kg | [Amazon.co.jp — 塩ビパイプ VU100 1 m](https://www.amazon.co.jp/%E8%BE%B2%E6%A5%AD%E5%B1%8B-%E5%A1%A9%E3%83%93%E3%83%91%E3%82%A4%E3%83%97%EF%BC%B6%EF%BC%B5%EF%BC%91%EF%BC%90%EF%BC%90-%EF%BC%91%EF%BD%8D/dp/B00DPGDJKE) (~¥700–1,500); [0.5 m version](https://www.amazon.co.jp/%E3%83%93%E3%83%8B%E3%83%BC%E3%83%AB%E3%83%91%E3%82%A4%E3%83%97-VU100%EF%BC%88%E5%A4%96%E5%BE%84%E7%B4%84114%E3%83%9F%E3%83%AA%CE%A6%EF%BC%89%C3%97%E9%95%B7%E3%81%95-%E7%B4%840-5%EF%BD%8D%EF%BC%88%E7%B4%8450%EF%BD%83%EF%BD%8D-%E5%AE%9F%E5%AF%B8%E7%B4%84495%E3%83%9F%E3%83%AA%EF%BC%89-%E5%A1%A9%E3%83%93%E3%83%91%E3%82%A4%E3%83%97%E3%83%BB%E7%A1%AC%E8%B3%AA%E5%A1%A9%E5%8C%96%E3%83%93%E3%83%8B%E3%83%BC%E3%83%AB%E3%83%91%E3%82%A4%E3%83%97/dp/B0DFNWDTJY) | Literally the "PVC pipe" row of the source list. Sold in 0.25 / 0.5 / 1 / 2 m lengths from the same sellers, giving a **free length sweep** — 0.5 vs 1 vs 2 m at fixed diameter is a direct measurement of how specular-lobe width trades against detectability. Buy end caps and it doubles as a buoyant-vs-flooded contrast. |
| **Steel scaffold tube (単管パイプ) 48.6 mm × 1.5 m, ~4.1 kg** | [MonotaRO — 単管パイプ 48.6](https://www.monotaro.com/s/q-%E5%8D%98%E7%AE%A1%E3%83%91%E3%82%A4%E3%83%97%2048.6/) (~¥1,500–2,500) | Same length class as the PVC pipe, far higher impedance contrast, self-sinking, and it is a real quayside object. The **PVC-vs-steel tube pair at matched length and near-matched diameter** is the second good material contrast in this catalogue. Also the building material for the F4 cube. |
| Conger-eel tube trap (アナゴ筒), 60–100 cm | [MonotaRO — 雑漁具 category](https://www.monotaro.com/s/c-135814/); also Rakuten (search 「アナゴ筒」) | Region-real, and a nice edge case: a thin-walled tube open at both ends, which should behave differently from a capped pipe. |
| Timber / sleeper, ~200 × 20 × 15 cm | Local home centre (transport by car; not worth shipping) | Low impedance contrast, may be near-neutrally buoyant when dry — a deliberately hard linear target and a useful counterpoint to the steel tube. |
| Wooden pallet, JIS T11 1100 × 1100 × 140 mm | Local pallet supplier or free from a warehouse | Large footprint, tiny relief, open slats. Sits at the intersection of F4 and F5 and is a realistic port object. Needs heavy ballast — it floats. |
 
---
 
### F6 — Tapered / conical
 
**Contains:** traffic cones, bollards, barricade feet, buoy cones.
 
**What it tests.** A cone has **no broadside** — its surface normal sweeps continuously, so there is
never a large in-phase reflecting area at any aspect. The USNA capstone found their pyramid harder to
detect than their cube of the same nominal size, which is exactly this effect. A cone is therefore the
cheapest available "predicted-hard but not predicted-invisible" control, and a much better one than a
plastic box because it fails for a *geometric* reason rather than a material one.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **PE traffic cone, 700 mm, 380 mm base, ~0.85 kg** | [Amazon.co.jp — カラーコーン 赤 H700mm](https://www.amazon.co.jp/%E3%82%AB%E3%83%A9%E3%83%BC%E3%82%B3%E3%83%BC%E3%83%B3-%E8%B5%A4-H700mm/dp/B00LFFS772) (~¥500–900) | Identical to the object in the source list, at the exact standard Japanese dimensions. 70 cm of relief on a 38 cm base is a lot of height for very little acoustic cross-section — a genuinely informative failure if it fails. Needs ballast (hollow, buoyant). |
| **Heavy PVC cone, 700 mm, 2.3 kg, thick-walled** | [Amazon.co.jp — 2 kg コーン 700 mm](https://www.amazon.co.jp/%E3%82%AB%E3%83%A9%E3%83%BC%E3%82%B3%E3%83%BC%E3%83%B3-2kg%E3%82%B3%E3%83%BC%E3%83%B3-%E3%82%AA%E3%83%AC%E3%83%B3%E3%82%B8-%E5%8D%98%E5%93%81-%E9%AB%98%E3%81%95%E7%B4%84700mm/dp/B00MEAC4M6) (~¥1,500) | Same geometry, ~3× the wall mass and a different polymer — a shape-matched material contrast within the family, and heavy enough to resist tidal current with only a light strop. Preferred if buying one. |
| 20-cone bulk set | [Amazon.co.jp — セールコーン 700 mm 20本セット](https://www.amazon.co.jp/%E3%82%AB%E3%83%A9%E3%83%BC%E3%82%B3%E3%83%BC%E3%83%B3-%E3%82%BB%E3%83%BC%E3%83%AB%E3%82%B3%E3%83%BC%E3%83%B3-700mm-20%E6%9C%AC%E3%82%BB%E3%83%83%E3%83%88-%E8%B5%A4/dp/B01N033QEW) (~¥8,150) | If you ever want a **spatial density experiment** — a field of N identical targets at known spacing to measure detection probability directly rather than inferring it from a handful of objects — this is by far the cheapest way to get 20 identical targets. Also useful as surface markers. |
 
---
 
### F7 — Toroid and low-profile compliant
 
**Contains:** car and truck tyres, motorcycle tyres, rubber boat fenders.
 
**What it tests.** The July disappearing-tyre case. Rubber has poor impedance contrast against water,
a tyre lying flat has almost no relief, and the toroidal shape has no flat face. This family is the
**predicted-hard control the design explicitly wants** — its job is to be marginal and intermittent,
and to demonstrate that the pinger-based ground truth can distinguish "the target moved" from "the
detector failed". Tyres are also genuinely one of the highest-frequency objects in Japanese fishing
harbours, so this is not a contrived control.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **Used car tyre, 14-inch class (~60 cm dia. × 18 cm)** | Free or near-free from any local tyre shop / ガソリンスタンド — ask for 廃タイヤ. If you must order: [Amazon.co.jp — 中古タイヤ 165/65R14, 4本セット](https://www.amazon.co.jp/%E3%80%90%E4%B8%AD%E5%8F%A4%E3%82%B9%E3%82%BF%E3%83%83%E3%83%89%E3%83%AC%E3%82%B9%E3%82%BF%E3%82%A4%E3%83%A4%E3%80%91BS-%E3%83%96%E3%83%AA%E3%82%B6%E3%83%83%E3%82%AF-65R14-4%E6%9C%AC%E3%82%BB%E3%83%83%E3%83%88-W14241216034/dp/B0DTTZ599N) | The real object. Prefer a **collection of identical tyres** over one, so that "invisible" can be shown to be reproducible rather than a one-off. Local disposal yards will usually give these away, which is both cheaper and more sustainable than shipping four. |
| Tyre **mounted on a steel wheel** | Same shops; ask for a wheel-and-tyre assembly | Critically useful: rim + tyre is the same silhouette with a large steel disc inside. If the bare tyre vanishes and the wheeled tyre does not, the material hypothesis is confirmed in one afternoon with one photograph. Order this if you order nothing else in F7. |
| Tyre stood **on edge** and staked | No purchase — a deployment variant | Converts a 18 cm-relief object into a 60 cm-relief object with zero change of material. The cheapest height sweep available anywhere in this catalogue. |
| Rubber boat fender, 40–70 cm | Marine chandlers (せんぐ屋, Rakuten — search 「ボートフェンダー」) | Real marina object; hollow, buoyant, needs ballast. Lower priority than tyres — same acoustic story, more money. |
 
---
 
### F8 — Tangled compliant mass
 
**Contains:** rope coils and mooring-line bundles, net balls and trawl offcuts, garden-hose coils,
cable.
 
**What it tests.** Rope and textile were 42 % of items in marina surveys — by frequency this is
arguably the most important family in the whole inventory, and it is the one least represented in AUV
shipwreck-derived training data. Acoustically it is the opposite of F1: a **diffuse, rough,
many-scatterer volume** with no specular face at all. Expect a weak but broadly aspect-independent
return and a fuzzy, unstable outline — a distinct detector signature worth characterising in its own
right, and a likely source of false positives against sediment texture.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **PP/nylon mooring rope, 12–16 mm × 20–30 m, coiled to ~50 cm** | Any chandler or home centre; MonotaRO and Amazon both stock (search 「クレモナロープ 16mm」 / 「PPロープ」) | The literal object. Coil size is a free variable: the same rope coiled to 30, 50 and 80 cm gives a controlled size sweep of a single physical object, which no other family offers. Sinking types (クレモナ / nylon) preferred over floating PP. |
| **Fishing net offcut, balled** | [MonotaRO — 漁網 / 雑漁具 category](https://www.monotaro.com/s/c-135814/); or offcuts free from a local fishing co-op | Net balls are called out explicitly in the source list. A co-op will usually hand over scrap netting, and the "compacted ball of indeterminate shape" caveat in the source document is best addressed by using genuinely scrap material rather than new. |
| Garden-hose coil, 30–60 cm dia. | Any home centre | Cheap, dense, holds its shape better than rope — a mid-point between F8 and F5. |
 
**Rigging note.** Compliant targets change shape between deployments. Photograph and measure each one
on deck before every drop and log the configuration, or the family becomes uninterpretable.
 
---
 
### F9 — Small hard threshold objects
 
**Contains:** glass bottles (一升瓶 39.8 cm, beer 大瓶 31 cm), 2 L PET bottles, cans.
 
**What it tests.** These sit at or below the along-track resolution cell at working ranges and are
included **as deliberate predicted-invisible controls** — objects whose non-detection is a
measurement, not a failure. Glass has the better impedance contrast of the two and sinks
unballasted; PET is near-neutral and needs filling. Both are among the highest-frequency real seabed
items in Japanese waters, so their detectability floor is operationally meaningful, not academic.
 
**Surrogates:**
 
| Object | Where to order | Why it is the right stand-in |
|---|---|---|
| **一升瓶 (1.8 L sake bottle), 39.8 cm × ~10.5 cm dia.** | Free from any liquor store or restaurant; also sold empty on Rakuten (search 「一升瓶 空瓶」) | The tallest single item in this family and distinctly Japanese. Sinks when filled with water, no ballast needed. Glass–water contrast is modest but real. |
| Beer 大瓶 (633 mL), 31 cm | Same | Second point on a length axis with the same material and diameter class. |
| **2 L PET bottle**, 31 × 9 cm | Any convenience store | Top seabed item in Osaka Bay per the source document. Fill with sand for a hard target, with water for a near-invisible one — one object, two experiments. |
 
**Design rule.** Deploy these in a known cluster with RTK-fixed corners rather than singly. A cluster
that produces one blob rather than four contacts is itself a resolution measurement.
 
---
 
## 4. Matched pairs — the controlled contrasts worth building in
 
The single biggest weakness of an ad-hoc target set is that every object differs from every other in
several ways at once, which is exactly the "one independent variable per phase" problem the July
campaign ran into. Five pairs in this catalogue vary **one** thing:
 
| Pair | Variable isolated | Cost |
|---|---|---|
| 一斗缶 (steel) vs 50 L folding container (PP), similar envelope | Material, at roughly matched box geometry | ~¥3,500 |
| Steel pail can 20 L vs plastic pail can 20 L | Material, at *identical* geometry | ~¥2,500 |
| 50 L solid-wall container vs 50 L mesh container | Fill fraction, identical envelope and material | ~¥4,000 |
| PVC VU100 tube vs steel 単管 tube, both ~1 m | Material, at matched length and near-matched diameter | ~¥3,500 |
| Bare tyre vs tyre on steel rim | Internal reflector, identical silhouette | ~free |
| PVC pipe at 0.5 / 1 / 2 m | Length, at fixed diameter and material | ~¥3,000 |
| Concrete block ×1 / ×2 / ×3 stacked | Height, at fixed footprint and material | ~¥1,000 |
| Tyre lying flat vs standing on edge | Relief, at fixed material and mass | free |
 
Seven controlled contrasts for under ¥20,000 total, each answerable in a single afternoon of paired
passes. This is the cheapest possible route to a defensible detectability characterisation.
 
---
 
## 5. Recommended purchase tiers
 
### Tier 1 — buy first (~¥15,000, covers all nine families at one point each)
 
1. 一斗缶 18 L × 2 — F1
2. Steel pail can 20 L × 1 **and** plastic pail can 20 L × 1 — F2 + material pair
3. Concrete blocks × 10 — F3 + universal ballast
4. Mesh folding container 50 L × 1 **and** solid folding container 50 L × 1 — F4 + fill-fraction pair
5. PVC pipe VU100 1 m × 2, plus one 0.5 m and one 2 m — F5 + length sweep
6. Heavy PVC traffic cone 700 mm × 2 — F6
7. Used car tyres × 3, one on a rim — F7 (free locally)
8. Sinking rope 16 mm × 30 m — F8
9. 一升瓶 × 2, 2 L PET × 2 — F9 (free)
### Tier 2 — add once Tier 1 has produced first results
 
- Steel 単管 tube 1.5 m × 2 (completes the F5 material pair)
- Fire extinguisher, 10-型 (dense small cylinder)
- Octopus pot with cast-in ballast × 2 (region-real, drop-and-go)
- Junk bicycle × 1 (the flagship F4 object)
- Crab/whelk folding pot × 2
- Scrap net ball from a local co-op
### Tier 3 — only if the campaign schedule allows
 
- 200 L empty steel drum (needs lifting gear, permission, and a plan)
- 20-cone bulk set for a spatial-density / detection-probability field
- Wooden pallet and sleeper (transport-limited, car only)
---
 
## 6. Rigging, ballasting, recovery, permissions
 
**Ballast changes the acoustics, so log it.** Every hollow target needs weight. Two options, and they
are not equivalent:
 
- **External ballast** — object strapped to a concrete block on a 20–30 cm strop. Preserves any
  internal air, keeps the object's own acoustic properties intact, but adds a second target to the
  scene. Preferred for the material-contrast pairs, since the block is common to both arms and
  cancels out.
- **Internal flooding / sand fill** — no extra object in the scene, but changes the target's internal
  impedance completely. Fine for F9 and for anything where the shell dominates.
Record which was used, per object, per deployment. A can that was air-filled on Tuesday and flooded
on Thursday is two different targets.
 
**Rigging.** Every object leaves the water. Rig each with a marked recovery line to a small subsurface
float, or to a numbered surface buoy set well clear of the survey lines so it does not appear in the
imagery. Take an RTK fix at the moment of release, and note that the object does not land where it
was released — it kites. The USBL pinger on the instrumented target exists precisely to resolve this,
and after the July tyre episode at least one object per session should carry it.
 
**Position discipline.** Log the *bearing* each elongated target was laid on, not just its position.
For F5 and F1 the seabed orientation is the independent variable of the whole aspect experiment, and
it is unrecoverable after the fact.
 
**Permissions and environment.** Deploying objects on a fishing-harbour bed requires the harbourmaster's
and usually the fishing cooperative's agreement. Frame it as a recoverable, same-day, fully-inventoried
deployment with a written object list and count-in/count-out. Nothing plastic, buoyant or fragmenting
should be left even briefly unattended. Concrete blocks, steel cans and glass bottles are the easiest
to justify; tyres, netting and PET the hardest, despite being the most realistic.
 
---
 
## 7. Caveats on the surrogate mapping
 
1. **Real objects are not product-shaped.** The source document says this and it is the main limit
   here: a new 一斗缶 is a clean rectangular prism, and a real one on a harbour floor is dented,
   partly buried, biofouled and half-full of sediment. Everything in this catalogue systematically
   over-estimates detectability for that reason.
2. **Biofouling and sediment interaction are not simulated at all.** A target deployed for two hours
   is acoustically nothing like one that has been down for two years. The source document's note that
   fouling can double an acoustic footprint while hiding an object optically cuts directly against
   any inference from these trials to real-litter surveys.
3. **The family scheme is a hypothesis, not a result.** It groups objects by what *should* matter —
   flat face, curved face, fill fraction, taper, material, compliance. Whether those axes actually
   predict detector behaviour is the thing being tested. If two families turn out to be
   indistinguishable in the data, that is a finding, and the scheme should be collapsed accordingly.
4. **Frequency-of-occurrence and detectability are not correlated.** The most common real objects
   (rope, film, PET, small fragments) are among the hardest to detect, and the most detectable
   (drums, blocks, metal cans) are relatively rare. A detector trained and evaluated on this target
   set will over-report the easy classes. Any operational claim must be weighted by the density
   figures in §3.3 and §4 of the source document, not by per-object detection rates.
5. **Nothing here validates the resolution or shadow models.** These objects are the instrument for
   testing those models. If the measurements contradict the geometric predictions, the measurements
   win.
---
 
*End of target families and surrogates.*
