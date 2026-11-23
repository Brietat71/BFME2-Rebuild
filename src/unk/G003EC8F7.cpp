// Generated from the ledger; map snapshot c591f7146f88c8a8248ebb8ae22f0c978c22aed463db64e05ef57ff0dfae99cc
// object=G003EC8F7 name-evidence=invented
// Extents and edges are hypotheses; byte verification alone does not establish original TU boundaries.
#include "Common/GameType.h"
// FUNCTION: BFME2 0x003EC8F7 size=43 name=?ComputeCRC@@YAIPBEII@Z evidence=N:ledger tier=B hypothesis:mm1-gap-unit
UnsignedInt ComputeCRC(const UnsignedByte *data, UnsignedInt length, UnsignedInt crc)
{
	if (data)
	{
		while (length > 0)
		{
			int hibit = (crc & 0x80000000) ? 1 : 0;
			crc <<= 1;
			crc += *data++;
			crc += hibit;
			--length;
		}
	}
	return crc;
}
