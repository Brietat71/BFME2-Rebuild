# Nightly build of main 4ae67eed04: **PARTIAL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | success: 3250 of 3250 files compiled, 526 match completely |
| Linking | 6,021 of 9,305 names our written code refers to are provided (64.7%); 3,284 missing, 14 defined twice |
| Whole program | 15,885 of 41,565 functions of the original program are defined (38.2%) |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 6.3 to 15.9 min; median batch of 8 files 14.1 to 35.6 s across machines.
Wall time 17.0 min; runner minutes by stage {"compile": 174.2}.
