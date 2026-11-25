# Vendored releases

## `stlport-4.6/`: STLport 4.6, as released

`stlport-4.6/` is the complete contents of the STLport 4.6 release archive (its top
directory `STLport-4.6/`), byte for byte.

| | |
|---|---|
| Release | STLport 4.6 (`_STLPORT_VERSION 0x460`) |
| Archive | <https://sourceforge.net/projects/stlport/files/STLport%20archive/STLport%204/STLport-4.6.tar.gz> |
| Archive SHA-256 | `744dd31ac34246bdba4ef50f79b4d936c842a3e4f13915a86cc06f7c7cf84f60` (gzip header dated 2003-10-31) |
| Files | 970 (`stlport-4.6.SHA256SUMS` lists each file's SHA-256 as the archive ships it) |
| Licence | the STLport licence (HP, SGI, Silicon Graphics, Moscow Center for SPARC Technology, Boris Fomitchev), in `stlport-4.6/README` and in each file's header |

`.gitattributes` turns off line-end conversion for the tree, so the 30 files the
archive ships with CR LF line ends (and its eight binary files) stay as they are.
Git does not store directories, so the archive's two empty directories
(`lib/obj/`, `test/eh/obj/`) are absent. The seven files the archive marks as
executable are executable here.

Check the tree against the archive's contents:

```sh
cd vendor/stlport-4.6 && sha256sum -c ../stlport-4.6.SHA256SUMS
```

Retail `game.dat` 1.06 linked this release (not 4.6.1 or 4.6.2): see
`include/upstream/stlport-4.6/PROVENANCE.md` for the `ios_base::Init` and
`locale` bodies that tell the three releases apart.
