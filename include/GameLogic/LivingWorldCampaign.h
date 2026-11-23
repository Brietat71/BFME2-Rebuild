#pragma once

#include "Common/AsciiString.h"
#include "Common/GameType.h"
#include "Common/Snapshot.h"
#include "Common/Vector.h"

class LWPlayerDef;
class Rva003F9258Data;
class Rva004FD1BC;
class Rva0056616B;
class INI;

// 0x0052D0B4 allocates 0x50 bytes and 0x0052CF0F installs the
// four-slot Snapshot table. INI field names come from table 0x008688A8.
class LivingWorldCampaign : public Snapshot
{
public:
    explicit LivingWorldCampaign(const AsciiString &name);
    virtual ~LivingWorldCampaign();

    void CreatePlayers();
    Int AdjustStartingPositionForScenario(Int position);
    void AddPlayer(const LWPlayerDef &player);
    static void ParseLivingWorldCampaignBlock(INI *ini);
    virtual const char *GetSnapshotName() const;
    virtual void xfer(Xfer *xfer);

protected:
    virtual void loadPostProcess() {} // slot 1, native 0x000B3FD0

private:
    AsciiString m_name;
    Int m_unk0x08; // saved as a signed integer by 0x0052BAFE
    _STL::vector<Rva0056616B> m_acts; // 0x00566D83 constructs the Act record, stride 0xB8
    Int m_initialActIndex; // 0x0052C0C8 selects the first enabled act
    Rva004FD1BC *m_scenario; // Scenario parser 0x004FD94E and setter 0x004FC8B3
    Rva003F9258Data *m_tutorial; // Tutorial parser 0x003F9258 and setter 0x003F7BE9
    _STL::vector<LWPlayerDef> m_players; // AddPlayer at 0x0052D394 uses stride 0x28
    AsciiString m_localPlayer;
    AsciiString m_scriptHolder;
    Int m_secondsPerReinforcement;
    UnsignedInt m_startingCashRTS;
    UnsignedInt m_startingCashRTSWithFort;
    Real m_initialRevivalCostMultiplier;
    Real m_initialRevivalTimeMultiplier;
    Bool m_isScriptedCampaign;
    Bool m_isEvilCampaign;
    Bool m_forceAdvanceTurnPhase;
};

typedef char LivingWorldCampaignSize[(sizeof(LivingWorldCampaign) == 0x50) ? 1 : -1];
