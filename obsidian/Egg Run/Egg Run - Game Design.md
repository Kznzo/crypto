---
tags: [egg-run, design]
updated: 2026-11-27
---
# Egg Run: game design

Back to [[Egg Run - Start Here]]

## Core loop

1. **Run** down the canyon until your **stamina** runs out.
2. You **hatch the egg of the furthest zone** you reached. Further zones give better eggs.
3. Each egg rolls a **rarity** and hatches a **cute animal**.
4. Your team of 3 **auto-battles NPC waves** in the **Battle Box** for **coins**.
5. Coins buy **Speed** and **Stamina** upgrades, so you run further and reach better eggs.
6. At your **base**, you stand on the **training pad** and your team gains XP. (Later: a treadmill from my folk-treadmills skill.)

## Decisions (my picks)

| Question | Choice |
|---|---|
| Arena opponents | **NPC enemies**: waves that get harder |
| What limits the run | **Stamina + speed**, both upgradable with coins; animals add speed |
| Fight style | **Auto-battle**: stats and training decide |
| Animals | **Cute real animals**, with glowing Legendary and Mythic versions |

## Rarities and animals (4 per rarity)

| Rarity | Power | Health | Speed bonus | Release value | Animals |
|---|---|---|---|---|---|
| Common | 10 | 60 | +1 | 5 | Puppy, Kitten, Bunny, Chick |
| Uncommon | 22 | 132 | +2 | 12 | Fox, Piglet, Duckling, Lamb |
| Rare | 48 | 288 | +3 | 30 | Panda, Penguin, Koala, Owl |
| Epic | 105 | 630 | +5 | 80 | Lion, Tiger, Wolf, Polar Bear |
| Legendary | 230 | 1380 | +8 | 250 | Golden Lion, Crystal Fox, Ice Wolf, Ruby Panda |
| Mythic | 520 | 3120 | +12 | 800 | Galaxy Cat, Cosmic Tiger, Rainbow Bunny, Celestial Deer |

Each animal gets a quality roll (×0.9 to ×1.1). Each level adds +12% power and +10% health, up to level 50. XP to the next level = 15 × level^1.6. Team size 3, inventory 60.

## Eggs = corridor zones (Voxel Stud Egg Pack)

| # | Zone | Starts at (studs) | Egg | Odds |
|---|---|---|---|---|
| 1 | Meadow | 0 | Grass Egg | C 82 · U 16 · R 2 |
| 2 | Farm | 150 | Speckled Egg | C 62 · U 30 · R 7 · E 1 |
| 3 | Hive | 350 | Bee Egg | C 42 · U 36 · R 17 · E 5 |
| 4 | Beach | 600 | Ocean Egg | C 25 · U 38 · R 27 · E 9 · L 1 |
| 5 | Snow | 950 | Frost Egg | C 12 · U 32 · R 35 · E 17 · L 3.5 · M 0.5 |
| 6 | Volcano | 1400 | Lava Egg | U 22 · R 40 · E 28 · L 8.5 · M 1.5 |
| 7 | Storm | 2000 | Storm Egg | U 8 · R 35 · E 38 · L 15 · M 4 |
| 8 | Crystal | 2700 | Crystal Egg | R 24 · E 44 · L 25 · M 7 |
| 9 | Golden | 3500 (to 4200) | Golden Egg | E 40 · L 45 · M 15 |

Eggs are earned by running, not bought, so they aren't paid random items. The odds will still be shown in the game.

## Upgrades (coins)

| Upgrade | Starts at | Per level | Max level | Cost of the next level |
|---|---|---|---|---|
| Speed | WalkSpeed 16 | +2 | 30 | 40 × 1.32^level |
| Stamina | 8 s | +1.5 s | 40 | 50 × 1.36^level |
| Training | 2 XP/s | +1 | 25 | 80 × 1.45^level |

Run distance ≈ speed × stamina. WalkSpeed is capped at 120, including the animal bonuses.

## Battle Box (NPC waves)

- An enemy fighter at level L has power = 8 × 1.2^(L-1) and health = power × 6.
- Team size: 1 enemy from level 1, 2 from level 5, 3 from level 15.
- Reward for a win: 25 × 1.17^(L-1) coins, plus XP for each of my fighters (6 + 2 × L).
- Rules: at most 25 rounds, 12% crit chance at ×1.6, a draw counts as a loss.
- You can fight any level up to your best + 1. The server simulates the fight and the client plays it back in the arena.

## Balance (Python simulation of a typical player)

| Milestone | Time |
|---|---|
| Zone 2 | ~2 min |
| Arena 10 | 4-12 min |
| Zone 4 | 8-20 min |
| Zone 6 | 35-65 min |
| Zone 9 (Golden) | ~4.5-5.5 h |
| Arena 30 | ~4-6 h |

All these numbers live in `games/egg-run/src/ReplicatedStorage/EggRun/Config.luau`. Change them there.
