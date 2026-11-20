# Nightly build of main fb0d281c94: **PARTIAL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | success: 3253 of 3253 files compiled, 409 match completely |
| Linking | 5,181 of 8,317 names the rebuilt program needs are provided (62.3%); 3,136 missing |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 10.0 to 26.4 min; median batch of 8 files 23.2 to 61.3 s across machines.
Wall time 27.7 min; runner minutes by stage {"compile": 365.7}.
