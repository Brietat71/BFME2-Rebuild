# Nightly build of main 0fc7d30e48: **FAIL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | failure: 2843 of 2843 files compiled, 482 match completely |
| Linking | 5,010 of 8,253 names our written code refers to are provided (60.7%); 3,243 missing, 13 defined twice |
| Whole program | 13,996 of 41,566 functions of the original program are defined (33.7%) |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 9.5 to 35.2 min; median batch of 8 files 22.3 to 86.0 s across machines.
Wall time 36.7 min; runner minutes by stage {"compile": 433.8}.
