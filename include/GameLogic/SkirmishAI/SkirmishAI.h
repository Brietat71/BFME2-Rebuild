// SkirmishAI.h: one computer player's skirmish brain, SIZE 0x188 (AIGameTeam::addPlayer allocates that many bytes). It
// derives from AIBuilder, whose 0x15C bytes come first. The constructor stores the owning player at +0x15C and its second
// argument, the army definition TheArmyDefinitionManager returns for the player, at +0x160, zeroes the phase fields, takes
// the logic frame at +0x174, sets the master index to -1, and builds the named-value map at +0x17C and a TacticalAI at
// +0x164. A brain is either a master (no master index) or is slaved to another computer player's brain:
// doSpecialSlaveAIUpdate gives the master player the AI's army-strength value, and doSpecialMasterAIDying hands a dying
// master's role to the first slave that resetMaster finds. update runs the phase tracker and AIBuilder::update, then the
// tactical AI; when the player is dead it hands its units over (master or slave) and marks the brain finished (+0x168).
// DoXfer transfers the members in order. Role names only where the code shows the role; offsets are the constructor's.
#pragma once
#ifndef BFME2_SKIRMISHAI_H
#define BFME2_SKIRMISHAI_H

#include <stddef.h>
#include <map>
#include "Common/GameType.h"
#include "Common/AsciiString.h"
#include "GameLogic/SkirmishAI/AIBuilder.h"

class Object;
class Player;
class Team;
class TacticalAI;
class Xfer;

class SkirmishAI : public AIBuilder
{
public:
	SkirmishAI(Player *player, void *unk, Bool flag);
	void DoXfer(Xfer *xfer);
	void update();
	Bool isAPartialBrain();
	void doSpecialSlaveAIUpdate();
	Int resetMaster();
	void updatePhase();
	void Register(Team *team);
	void UnRegister(Team *team);
	void onUnitCreated(Object *factory, Object *unit);
	void onHordeCreated(Object *factory, Object *unit);
	void transferUnitsToPlayer(Player *player);
	void doSpecialMasterAIDying();
	void doSpecialSlaveAIDying();
	void registerProducedObject(Object *object);	// AIBuilder's unless the brain has finished
	void unRegisterProducedObject(Object *object);
	Bool isMaster() const;
	void setMasterPlayerIndex(Int index);
	Bool hasNamedValue(const AsciiString &key);
	void setNamedValue(const AsciiString &key, Int value);
	Int getNamedValue(const AsciiString &key);	// zero, and the key is created, when absent

	Player *m_player;	// +0x15C
	void *m_armyDefinition;	// +0x160 the army definition TheArmyDefinitionManager returns for the player; the constructor's second argument
	TacticalAI *m_tacticalAI;	// +0x164
	Bool m_finished;	// +0x168 set once the owning player's death has been handled
	Int m_phase;	// +0x16C 0, 1 or 2; updatePhase advances it as the frame counts reach the player's phase times
	Real m_phaseProgress;	// +0x170 the fraction of the current phase that has passed
	UnsignedInt m_phaseStartFrame;	// +0x174 the logic frame the brain was created
	Int m_masterPlayerIndex;	// +0x178 -1 for a master
	_STL::map<AsciiString, Int> m_namedValues;	// +0x17C
};
typedef char SkirmishAISize[(sizeof(SkirmishAI) == 0x188) ? 1 : -1];
typedef char SkirmishAINamedValuesOffset[(offsetof(SkirmishAI, m_namedValues) == 0x17C) ? 1 : -1];

#endif
