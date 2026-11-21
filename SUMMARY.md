# Nightly build of main 9fa818c2b3: **FAIL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | failure: 2640 of 2640 files compiled, 420 match completely |
| Linking | 4,679 of 8,296 names our written code refers to are provided (56.4%); 3,617 missing, 13 defined twice |
| Whole program | 13,334 of 41,565 functions of the original program are defined (32.1%) |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 11.0 to 25.6 min; median batch of 8 files 25.2 to 58.9 s across machines.
Wall time 26.7 min; runner minutes by stage {"compile": 262.5, "publish": 0.0}.
