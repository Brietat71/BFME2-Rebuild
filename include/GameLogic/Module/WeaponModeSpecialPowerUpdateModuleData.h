// Weapon-mode configuration. The native constructor at 0x00494D26 calls
// SpecialPowerUpdateModuleData, then initializes the fields from its own
// INI table at VA 0x00C4E8B0.
#pragma once
#ifndef BFME2_WEAPON_MODE_SPECIAL_POWER_UPDATE_MODULE_DATA_H
#define BFME2_WEAPON_MODE_SPECIAL_POWER_UPDATE_MODULE_DATA_H

#include <stddef.h>
#include "Common/BitFlags.h"
#include "GameLogic/Module/SpecialPowerUpdateModule.h"

enum WeaponSlotType;

class MultiIniFieldParse;
class INI;
class WeaponModeSpecialPowerUpdateModuleData : public SpecialPowerUpdateModuleData
{
public:
	static void buildFieldParse(MultiIniFieldParse &parse);
	static ModuleData *friend_newModuleData(INI *ini);
	WeaponModeSpecialPowerUpdateModuleData();
	virtual ~WeaponModeSpecialPowerUpdateModuleData();

	AsciiString m_attributeModifier;
	UnsignedInt m_duration;
	WeaponSlotType m_lockWeaponSlot;
	WeaponSetFlags m_weaponSetFlags;
};

typedef char WeaponModeSpecialPowerUpdateModuleData_size[(sizeof(WeaponModeSpecialPowerUpdateModuleData) == 0x34) ? 1 : -1];
typedef char WeaponModeSpecialPowerUpdateModuleData_attribute[(offsetof(WeaponModeSpecialPowerUpdateModuleData, m_attributeModifier) == 0x18) ? 1 : -1];
typedef char WeaponModeSpecialPowerUpdateModuleData_lock[(offsetof(WeaponModeSpecialPowerUpdateModuleData, m_lockWeaponSlot) == 0x20) ? 1 : -1];
typedef char WeaponModeSpecialPowerUpdateModuleData_flags[(offsetof(WeaponModeSpecialPowerUpdateModuleData, m_weaponSetFlags) == 0x24) ? 1 : -1];

#endif
