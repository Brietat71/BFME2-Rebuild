// ActionManager holds no data beyond SubsystemInterface. The allocation
// at 0x0022FA6C is 0xC bytes. Its ctor at 0x0041B8B5 calls the base and
// installs its table, whose init, reset and update slots select bare ret.
#pragma once

#include "Common/SubsystemInterface.h"

class Coord3D;
class Object;
class Player;
class SpecialPowerTemplate;

enum AbleToAttackType;
enum CanAttackResult;
enum CanEnterType;
enum CommandSourceType;
enum WeaponSlotType;

class ActionManager : public SubsystemInterface
{
public:
	ActionManager(); // 0x0041B8B5
	virtual ~ActionManager(); // 0x0041B8C7
	virtual void init() {}
	virtual void reset() {}
	virtual void update() {}
	// 0x0041CC65: is the position inside the pathfind extent shrunk by the power's cursor radius
	bool rva0041CC65(const SpecialPowerTemplate *power, const Coord3D *pos);
	bool canOverrideSpecialPowerDestination(Object *obj, const Coord3D *pos, int idx, int unused); // 0x0041BB49
	unsigned char canFireWeapon(const Object *obj, WeaponSlotType slot, CommandSourceType commandSource); // 0x0041BB26
	bool rva0041BAD2(const Object *obj, const Object *victim, CommandSourceType commandSource, WeaponSlotType slot); // 0x0041BAD2 (fire at an object target; the map has no real name yet)
	bool canFireWeaponAtLocation(const Object *obj, const Coord3D *pos, CommandSourceType commandSource, WeaponSlotType slot, const Object *victim); // 0x0041C085
	CanAttackResult bfmeGetCanAttackContained(const Object *obj, const Object *victim, CommandSourceType commandSource, AbleToAttackType attackType); // 0x0041BFA2: the best result the victim's attackers inside the object's contain module can reach
	CanAttackResult getCanAttackObject(const Object *obj, const Object *victim, CommandSourceType commandSource, AbleToAttackType attackType); // 0x0041C6CF
	bool canPlayerGarrison(const Player *player, const Object *target, CommandSourceType commandSource); // 0x0041C21B
	bool canResumeConstructionOf(const Object *object, const Object *b, CommandSourceType commandSource); // 0x0041BF47
	bool canMakeObjectDefector(const Object *obj, const Object *objectToMakeDefector, CommandSourceType commandSource);
	bool canGetRepairedAt(const Object *obj, const Object *repairDock, CommandSourceType commandSource); // 0x0041BBE4 (AIUpdateInterface::privateGetRepaired 0x0026DDBB)
	bool canGetHealedAt(const Object *obj, const Object *healDest, CommandSourceType commandSource); // 0x0041BE93 (AIUpdateInterface::privateGetHealed 0x0026DD89)
	bool canDoSpecialPowerAtObject(const Object *source, const Object *target, CommandSourceType commandSource, const SpecialPowerTemplate *power, unsigned int commandOptions, bool flag); // 0x0041CFCC (GrabPassengerSpecialPower::doSpecialPowerAtObject 0x004C504E)
	bool canEnterObject(const Object *obj, const Object *target, CommandSourceType commandSource, CanEnterType modifier, bool flag, bool *outFlag); // 0x0041C2D0 (the map files it under class BFMEActionManager; every other ActionManager row and the function-local statics of canDoSpecialPowerAtObject/canTransferSuppliesAt say ActionManager)
	bool Rva0041B94AGet(Object *obj, Object *target, int commandSource); // 0x0041B94A (AIUpdateInterface::privateMoveToObject 0x0026472F)
	bool canTransferSuppliesAt(const Object *obj, const Object *dest);
	bool canConvertObjectToCarBomb(const Object *obj, const Object *objectToConvert, CommandSourceType commandSource);
	bool canHijackVehicle(const Object *obj, const Object *objectToHijack, CommandSourceType commandSource);
	bool canDockAt(const Object *obj, const Object *dockDest, CommandSourceType commandSource, bool checkClearToUse);
	bool canRepairObject(const Object *repairer, const Object *target, CommandSourceType commandSource); // 0x0041CE99 (DozerAIUpdate::update 0x00489800 and privateRepair 0x00488AC9 call it)
};

typedef char ActionManagerSize[(sizeof(ActionManager) == 0xC) ? 1 : -1];

extern ActionManager *TheActionManager; // 0x00E030E8
