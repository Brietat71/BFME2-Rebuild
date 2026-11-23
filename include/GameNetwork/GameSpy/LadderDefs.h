// LadderDefs.h: the GameSpy ladder descriptions the quick-match and custom lobbies read (Zero Hour's LadderInfo and
// LadderList by role and member order, GPL-3.0-or-later; the offsets and sizes are retail's).
// Portions derived from Command & Conquer Generals and Command & Conquer Generals Zero Hour, (c) Electronic Arts Inc., GPL-3.0-or-later; see LICENSE and NOTICE.
// Target facts (code RVAs):
//  - A LadderInfo is 0x3C bytes. Its address string is at +0x28 and its port at +0x2C (findLadder 0x0054D74B compares both),
//    the valid-map list at +0x1C, the two flag bytes checkLadder 0x0054E2FB clears at +0x1A and +0x1B, and the index at +0x38.
//  - A LadderList is three list heads of one pointer each. findLadder walks +0x4, then +0x8, then +0x0; the constructor
//    0x0054E546 appends the parsed standard ladders to +0x8 and the special ones to +0x4, and checkLadder appends to +0x0.
#pragma once
#ifndef BFME2_LADDERDEFS_H
#define BFME2_LADDERDEFS_H

#include <list>
#include <stddef.h>
#include "Common/GameType.h"
#include "Common/AsciiString.h"
#include "Common/UnicodeString.h"

class LadderInfo
{
public:
	LadderInfo();										// 0x0054D858

	UnicodeString name;									// +0x00
	UnicodeString description;							// +0x04
	UnicodeString location;								// +0x08
	Int playersPerTeam;									// +0x0C
	Int minWins;										// +0x10
	Int maxWins;										// +0x14
	Bool randomMaps;									// +0x18
	Bool randomFactions;								// +0x19
	Bool validQM;										// +0x1A
	Bool validCustom;									// +0x1B
	_STL::list<AsciiString> validMaps;					// +0x1C
	_STL::list<AsciiString> validFactions;				// +0x20
	AsciiString cryptedPassword;						// +0x24
	AsciiString address;								// +0x28
	UnsignedShort port;									// +0x2C
	AsciiString homepageURL;							// +0x30
	Bool submitReplay;									// +0x34
	Int index;											// +0x38
};
typedef char LadderInfo_size[(sizeof(LadderInfo) == 0x3C) ? 1 : -1];
typedef char LadderInfo_validMaps[(offsetof(LadderInfo, validMaps) == 0x1C) ? 1 : -1];
typedef char LadderInfo_address[(offsetof(LadderInfo, address) == 0x28) ? 1 : -1];
typedef char LadderInfo_port[(offsetof(LadderInfo, port) == 0x2C) ? 1 : -1];
typedef char LadderInfo_index[(offsetof(LadderInfo, index) == 0x38) ? 1 : -1];

typedef _STL::list<LadderInfo *> LadderInfoList;

class LadderList
{
public:
	LadderList();										// 0x0054E546

	const LadderInfo *findLadder(const AsciiString &addr, UnsignedShort port);	// 0x0054D74B

private:
	void loadLocalLadders();							// 0x0054E426
	void checkLadder(AsciiString fname, Int index);		// 0x0054E2FB

	LadderInfoList m_localLadders;						// +0x0
	LadderInfoList m_specialLadders;					// +0x4
	LadderInfoList m_standardLadders;					// +0x8
};
typedef char LadderList_size[(sizeof(LadderList) == 0xC) ? 1 : -1];

#endif
