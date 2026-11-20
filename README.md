# Battle for Middle-earth II rebuild: progress

How much of the original game (version 1.06) has been rebuilt as source code that compiles back to the same machine code. Measured automatically after every change; nobody edits this page.

Measured **20 November 2026**. The code figures describe commit [`69da5d735238`](https://github.com/Open-BFME/BFME2-Rebuild/commit/69da5d7352386882778ba9c6ba4a5934ffdd3be5) (20 November 2026, 19:03 UTC); the build checks run every day.

![Progress](progress.svg)

## The figures

![The four figures](detail.svg)

**Byte match**: `█████░░░░░░░░░░░░░░░` 25.8% (1,633,525 of 6,333,616 bytes)  
How much of the original game's code, by size, our source code compiles back to byte for byte.

**Linking**: `████████████░░░░░░░░` 62.3% (5,181 of 8,317 names)  
How many of the names the game needs to be assembled into one program our source already provides.
Measured by the daily build of commit [`fb0d281c946e`](https://github.com/Open-BFME/BFME2-Rebuild/commit/fb0d281c946e5c20b0602a6269515890de163ae1) (20 November 2026), which can be newer or older than the commit the other figures describe.

**Code proven**: `███░░░░░░░░░░░░░░░░░` 17.2% (1,089,034 of 6,333,616 bytes)  
How much of the code, by size, is byte-matched and also confirmed at every place it refers to other code or data, so the match cannot be a coincidence.

**Finished functions**: `█████░░░░░░░░░░░░░░░` 24.6% (10,222 of 41,565 functions)  
Functions that are proven, sit in a properly named source file, and belong to a class declared in a final header. Counted in functions, not bytes: small functions are often finished first, so this figure can be ahead of the byte figures.

## Does the rebuilt game run?

Nightly build of commit [`fb0d281c946e`](https://github.com/Open-BFME/BFME2-Rebuild/commit/fb0d281c946e5c20b0602a6269515890de163ae1) (20 November 2026): Compiles; the game run is not live yet (3,253 of 3,253 source files compile, 409 of them match the original completely).

- Starts: not run yet
- Reaches the main menu: not run yet
- Plays a skirmish: not run yet
- Equals the original game: not run yet
- Saves and loads: not run yet

## By part of the game

Byte match, by size, in each part of the source tree, largest part first.

| Part | Byte match | Bar |
| --- | ---: | --- |
| Game engine: GameLogic | 26.2% (388,095 of 1,483,402 bytes) | `█████░░░░░░░░░░░░░░░` |
| Game libraries | 50.1% (544,067 of 1,085,466 bytes) | `██████████░░░░░░░░░░` |
| Game engine: GameClient | 19.5% (163,263 of 837,736 bytes) | `████░░░░░░░░░░░░░░░░` |
| Platform layer: W3DDevice | 8.2% (42,826 of 522,891 bytes) | `██░░░░░░░░░░░░░░░░░░` |
| Game engine: Common | 34.0% (104,974 of 308,675 bytes) | `███████░░░░░░░░░░░░░` |
| Game engine: GameNetwork | 42.5% (91,322 of 214,687 bytes) | `█████████░░░░░░░░░░░` |
| GameSpy SDK (online library) | 98.4% (105,280 of 106,969 bytes) | `████████████████████` |
| Platform layer: MilesAudioDevice | 0.3% (189 of 64,798 bytes) | `░░░░░░░░░░░░░░░░░░░░` |
| Lua 4.0.1 (scripting library) | 96.7% (61,462 of 63,532 bytes) | `███████████████████░` |
| FESL (EA online library) | 0.0% (0 of 42,125 bytes) | `░░░░░░░░░░░░░░░░░░░░` |
| STLport 4.6 (C++ library) | 88.2% (28,615 of 32,452 bytes) | `██████████████████░░` |
| nbench (benchmark library) | 0.0% (0 of 26,290 bytes) | `░░░░░░░░░░░░░░░░░░░░` |
| zlib 1.1.4 (compression library) | 100.0% (23,719 of 23,719 bytes) | `████████████████████` |
| ppmalloc 1.26.11 (memory allocator) | 0.0% (0 of 14,445 bytes) | `░░░░░░░░░░░░░░░░░░░░` |
| LZHL 1.0 (compression library) | 99.7% (7,125 of 7,150 bytes) | `████████████████████` |
| Platform layer: Win32Device | 57.0% (1,564 of 2,742 bytes) | `███████████░░░░░░░░░` |
| Tools | 100.0% (744 of 744 bytes) | `████████████████████` |
| Not yet placed in a named file | 5.1% (70,280 of 1,391,260 bytes) | `█░░░░░░░░░░░░░░░░░░░` |
| Not yet assigned to any file | 0.0% (0 of 104,533 bytes) | `░░░░░░░░░░░░░░░░░░░░` |

Provisional class declarations still in use (files under `include/Draft/` that some source file includes): 9. Each should become a final header.

## Over time

![Progress over time](history.svg)

| Commit | Date | Byte match | Linking | Proven | Finished |
| --- | --- | ---: | ---: | ---: | ---: |
| [`69da5d735238`](https://github.com/Open-BFME/BFME2-Rebuild/commit/69da5d7352386882778ba9c6ba4a5934ffdd3be5) | 20 November 2026, 19:03 UTC | 25.79% | 62.29% (build `fb0d281`) | 17.19% | 24.59% |
| [`64fce00c1ee6`](https://github.com/Open-BFME/BFME2-Rebuild/commit/64fce00c1ee661f0ee508ad724887717cd302ecb) | 20 November 2026, 18:29 UTC | 25.69% | — | 16.91% | 24.19% |

How each figure is computed, with its exact formula: [ci/progress/README.md](https://github.com/Open-BFME/BFME2-Rebuild/blob/main/ci/progress/README.md).
