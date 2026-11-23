#include "Common/Rva003ECA69Element.h"
#include <string.h>
// Generated from the ledger; map snapshot c591f7146f88c8a8248ebb8ae22f0c978c22aed463db64e05ef57ff0dfae99cc
// object=G003ECA69 name-evidence=invented
// Extents and edges are hypotheses; byte verification alone does not establish original TU boundaries.
// FUNCTION: BFME2 0x003ECA69 size=24 name=?clear@Rva003ECA69Element@@QAEXXZ evidence=?:placeholder tier=B hypothesis:mm1-gap-unit
void Rva003ECA69Element::clear()
{
	m_value = 0.0f;
	memset(m_block, 0, sizeof(m_block));
}
