# Nightly build of main 5f2f839c07: **PARTIAL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | success: 3253 of 3253 files compiled, 409 match completely |
| Linking | 5,181 of 8,317 names our written code refers to are provided (62.3%); 3,136 missing, 7 defined twice |
| Whole program | 14,358 of 41,565 functions of the original program are defined (34.5%) |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 11.5 to 25.9 min; median batch of 8 files 24.9 to 60.1 s across machines.
Wall time 27.1 min; runner minutes by stage {"compile": 298.0, "publish": 0.0}.
