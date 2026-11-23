#include "Draft/_com_error.h"
// Generated from the ledger; map snapshot c591f7146f88c8a8248ebb8ae22f0c978c22aed463db64e05ef57ff0dfae99cc
// object=G006554E0 name-evidence=invented
// Extents and edges are hypotheses; byte verification alone does not establish original TU boundaries.
// FUNCTION: BFME2 0x006554E0 size=26 name=?WCodeToHRESULT@_com_error@@SAJG@Z evidence=N:ledger tier=B hypothesis:mm1-gap-unit
long _com_error::WCodeToHRESULT(unsigned short wCode)
{
	unsigned short code = wCode;
	if (code >= 0xFE00)
		return 0x8004FFFF;
	return 0x80040200 + code;
}
