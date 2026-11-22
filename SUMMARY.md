# Nightly build of main 275e5bc86e: **PARTIAL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | success: 3250 of 3250 files compiled, 525 match completely |
| Linking | 6,021 of 9,306 names our written code refers to are provided (64.7%); 3,285 missing, 14 defined twice |
| Whole program | 15,881 of 41,565 functions of the original program are defined (38.2%) |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 6.5 to 12.2 min; median batch of 8 files 14.5 to 28.9 s across machines.
Wall time 13.6 min; runner minutes by stage {"compile": 168.5, "publish": 0.0}.
