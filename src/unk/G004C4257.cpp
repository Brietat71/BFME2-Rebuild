// cl: /O1
// Generated from the ledger; map snapshot c591f7146f88c8a8248ebb8ae22f0c978c22aed463db64e05ef57ff0dfae99cc
// object=G004C4257 name-evidence=invented
// Extents and edges are hypotheses; byte verification alone does not establish original TU boundaries.
#include "GameLogic/Module/WeaponChangeSpecialPowerModuleData.h"
// FUNCTION: BFME2 0x004C4257 size=123 name=??0WeaponChangeSpecialPowerModuleData@@QAE@XZ evidence=N:ledger tier=B hypothesis:mm1-gap-unit
WeaponChangeSpecialPowerModuleData::WeaponChangeSpecialPowerModuleData() :
	m_toggleOnSleepFrames(0),
	m_toggleOffSleepFrames(0)
{
	m_flagsUsedForToggle.clear();
	m_toggleOnAttributeModifier.clear();
	m_toggleOffAttributeModifier.clear();
}
