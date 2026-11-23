#pragma once

#include "Common/AsciiString.h"
#include "Common/Coord2D.h"
#include "Common/GameType.h"
#include "Common/Snapshot.h"
#include "Common/Vector.h"

class Image;
class UnicodeString;

// The constructor at 0x004E30D5 installs the four-slot Snapshot table.
// Field names and offsets come from parseSpawnArmy's INI table at 0x008616C0.
class SpawnArmy : public Snapshot
{
public:
    explicit SpawnArmy(Int spawnArmyID);
    SpawnArmy(const SpawnArmy &other);
    virtual ~SpawnArmy();

    const Image *GetButtonImage(Int size);
    const Image *GetPortraitImage(Int size);
    UnicodeString GetButtonHelp(Int size);
    Int rva004E1755();    // 0x004E1755: the cost LivingWorldPlayer adds to its queued total
    virtual const char *GetSnapshotName() const;

protected:
    virtual void loadPostProcess() {} // slot 1, native 0x000B3FD0
    virtual void xfer(Xfer *xfer);

private:
    AsciiString m_icon;
    AsciiString m_banner;
    AsciiString m_constructButtonImage;
    AsciiString m_constructButtonTitle;
    AsciiString m_constructButtonHelp;
    AsciiString m_scriptingName;
    AsciiString m_tooltipStringTag;
    Coord2D m_position;
    AsciiString m_initialRegion;
    AsciiString m_playerArmy;
    AsciiString m_palantirMovie;
    AsciiString m_iconSize;
    _STL::vector<AsciiString> m_spawnForTemplates; // 0x0005A170 transfers 4-byte strings
    Real m_moveSpeed;
    Int m_buildTime;
    Int m_spawnArmyID; // 0x004E3991 transfers this as LivingWorldSpawnArmyID
    AsciiString m_heroTemplateName;
    Bool m_isCity;
    Bool m_spawnAtActStart;
};

typedef char SpawnArmySize[(sizeof(SpawnArmy) == 0x58) ? 1 : -1];
