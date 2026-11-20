# Nightly build of main 74a8dac093: **PARTIAL**

The nightly job compiles every source file, substitutes each file whose functions all match the original into the original program's link, links that image, plays it and compares the game state with the original program's recording, frame by frame.

| Stage | Result |
| --- | --- |
| Compile | success: 3253 of 3253 files compiled, 409 match completely |
| Linking | 5,181 of 8,317 names the rebuilt program needs are provided (62.3%); 3,136 missing |
| Link and play | not live yet: the private game image for this stage is not configured |

Compile shards took 10.3 to 27.5 min; median batch of 8 files 24.0 to 64.1 s across machines.
Wall time 31.3 min; runner minutes by stage {"compile": 302.0}.
